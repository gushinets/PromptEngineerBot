"""
Telegram bot message handlers and core logic.
"""

import logging
import re

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes
from tenacity import (
    RetryError,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from .config import BotConfig
from .conversation_manager import ConversationManager
from .dependencies import get_container
from .email_flow import get_email_flow_orchestrator
from .llm_client_base import LLMClientBase
from .messages import (
    BTN_CRAFT,
    BTN_EMAIL_DELIVERY,
    BTN_GENERATE_PROMPT,
    BTN_GGL,
    BTN_LYRA,
    BTN_LYRA_DETAIL,
    BTN_NO,
    BTN_RESET,
    BTN_YES,
    EMAIL_ALREADY_AUTHENTICATED,
    EMAIL_INPUT_MESSAGE,
    EMAIL_OTP_SENT,
    ERROR_EMAIL_INVALID,
    ERROR_EMAIL_RATE_LIMITED,
    ERROR_EMAIL_SEND_FAILED,
    ERROR_OTP_ATTEMPTS_EXCEEDED,
    ERROR_OTP_EXPIRED,
    ERROR_OTP_INVALID,
    ERROR_REDIS_UNAVAILABLE,
    ERROR_SMTP_UNAVAILABLE,
    FOLLOWUP_CHOICE_KEYBOARD,
    FOLLOWUP_CONVERSATION_KEYBOARD,
    FOLLOWUP_OFFER_MESSAGE,
    FOLLOWUP_PROMPT_INPUT_MESSAGE,
    OTP_VERIFICATION_SUCCESS,
    PROMPT_READY_FOLLOW_UP,
    RESET_CONFIRMATION,
    SELECT_METHOD_KEYBOARD,
    SELECT_METHOD_MESSAGE,
    WELCOME_MESSAGE,
    create_prompt_input_reply,
    get_processing_message,
    parse_followup_response,
    parse_llm_response,
)
from .prompt_loader import PromptLoader
from .state_manager import StateManager

logger = logging.getLogger(__name__)


def _is_network_error(exception: Exception) -> bool:
    """Check if an exception is a network-related error that should be retried."""
    if not exception:
        return False

    error_str = str(exception).lower()
    error_type = type(exception).__name__.lower()

    # Check for specific network-related error types
    network_error_types = [
        "connectionerror",
        "timeouterror",
        "networkerror",
        "timedout",
        "connecterror",
        "httpxconnecterror",
        "httpxtimeoutexception",
        "httpxnetworkerror",
    ]

    if error_type in network_error_types:
        return True

    # Check for network-related keywords in error message
    network_keywords = [
        "connect",
        "network",
        "timeout",
        "httpx",
        "connection",
        "timed out",
        "unreachable",
        "dns",
    ]

    return any(keyword in error_str for keyword in network_keywords)


class BotHandler:
    """Handles Telegram bot interactions and message processing."""

    def __init__(
        self, config: BotConfig, llm_client: LLMClientBase, sheets_logger_func=None
    ):
        self.config = config
        self.llm_client = llm_client

        # Get shared instances from dependency container
        container = get_container()
        self.state_manager = container.get_state_manager()
        self.prompt_loader = container.get_prompt_loader()
        self.conversation_manager = container.get_conversation_manager()
        self.log_sheets = sheets_logger_func or (lambda event, payload: None)

        # Initialize email flow orchestrator if available
        try:
            self.email_flow_orchestrator = get_email_flow_orchestrator()
        except RuntimeError:
            # Email flow orchestrator not initialized - will be set later if email feature is enabled
            self.email_flow_orchestrator = None

    def set_email_flow_orchestrator(self, orchestrator):
        """Set the email flow orchestrator after initialization."""
        self.email_flow_orchestrator = orchestrator

    def reset_user_state(self, user_id: int):
        """Reset the user's state and conversation history."""
        self.state_manager.set_waiting_for_prompt(user_id, True)
        self.state_manager.set_last_interaction(user_id, None)
        # Reset follow-up states
        self.state_manager.set_waiting_for_followup_choice(user_id, False)
        self.state_manager.set_waiting_for_followup_prompt_input(user_id, False)
        self.state_manager.set_in_followup_conversation(user_id, False)
        self.state_manager.set_improved_prompt_cache(user_id, None)
        # Reset email states
        self.state_manager.set_waiting_for_email_input(user_id, False)
        self.state_manager.set_waiting_for_otp_input(user_id, False)
        self.state_manager.set_email_flow_data(user_id, None)
        self.conversation_manager.reset(user_id)

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command or New Prompt button."""
        user_id = update.effective_user.id

        # Reset user state without logging tokens
        # Token logging should only happen when optimized prompts are generated
        self.reset_user_state(user_id)

        # Send welcome message
        await self._safe_reply(
            update,
            WELCOME_MESSAGE,
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True),
        )

        # Log session start
        logger.info(f"session_start | user_id={user_id}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages from users."""
        user_id = update.effective_user.id
        text = update.message.text
        user_state = self.state_manager.get_user_state(user_id)

        # Reset button always resets conversation
        if text == BTN_RESET:
            await self.handle_start(update, context)
            return

        # Handle email input waiting state
        if user_state.waiting_for_email_input:
            if self.email_flow_orchestrator:
                try:
                    await self.email_flow_orchestrator.handle_email_input(
                        update, context, user_id, text
                    )
                except Exception as e:
                    logger.error(f"Email input handling error for user {user_id}: {e}")
                    await self._safe_reply(
                        update, "❌ Email input error. Please try again later."
                    )
            else:
                await self._safe_reply(
                    update, "❌ Email service not available. Please try again later."
                )
            return

        # Handle OTP input waiting state
        if user_state.waiting_for_otp_input:
            if self.email_flow_orchestrator:
                try:
                    await self.email_flow_orchestrator.handle_otp_input(
                        update, context, user_id, text
                    )
                except Exception as e:
                    logger.error(f"OTP input handling error for user {user_id}: {e}")
                    await self._safe_reply(
                        update, "❌ OTP verification error. Please try again later."
                    )
            else:
                await self._safe_reply(
                    update, "❌ Email service not available. Please try again later."
                )
            return

        # Handle follow-up choice waiting state
        if user_state.waiting_for_followup_choice:
            # Check if this is part of an email flow
            email_flow_data = user_state.email_flow_data
            if email_flow_data and self.email_flow_orchestrator:
                # Email flow follow-up
                await self.email_flow_orchestrator.handle_followup_choice(
                    update, context, user_id, text
                )
            else:
                # Regular follow-up
                await self._handle_followup_choice(update, user_id, text)
            return

        # Handle follow-up prompt input waiting state
        if user_state.waiting_for_followup_prompt_input:
            # Check if this is part of an email flow
            email_flow_data = user_state.email_flow_data
            if email_flow_data and self.email_flow_orchestrator:
                # Email flow follow-up
                await self.email_flow_orchestrator.handle_followup_prompt_input(
                    update, context, user_id, text
                )
            else:
                # Regular follow-up
                await self._handle_followup_prompt_input(update, user_id, text)
            return

        # Handle follow-up conversation state
        if user_state.in_followup_conversation:
            # Check if this is part of an email flow
            email_flow_data = user_state.email_flow_data
            if email_flow_data and self.email_flow_orchestrator:
                # Email flow follow-up
                await self.email_flow_orchestrator.handle_followup_conversation(
                    update, context, user_id, text
                )
            else:
                # Regular follow-up
                await self._handle_followup_conversation(update, user_id, text)
            return

        # Handle prompt input
        if user_state.waiting_for_prompt:
            await self._handle_prompt_input(update, user_id, text)
            return

        # Handle method selection
        if self.conversation_manager.is_waiting_for_method(user_id):
            await self._handle_method_selection(update, context, user_id, text)
            return

        # Handle multi-turn conversation
        await self._handle_conversation_turn(update, user_id, text)

    async def _handle_prompt_input(self, update: Update, user_id: int, text: str):
        """Handle user prompt input."""
        self.conversation_manager.reset(user_id)
        self.conversation_manager.set_user_prompt(user_id, text)
        self.conversation_manager.append_message(user_id, "user", text)
        self.conversation_manager.set_waiting_for_method(user_id, True)

        user_state = self.state_manager.get_user_state(user_id)
        user_state.waiting_for_prompt = False

        # Log prompt received
        logger.info(
            f"prompt_received | user_id={user_id} | length={len(text)} | preview={text[:120]}"
        )

        # Show method selection with reset button
        method_keyboard = list(SELECT_METHOD_KEYBOARD.keyboard)
        method_keyboard.append([BTN_RESET])
        await self._safe_reply(
            update,
            SELECT_METHOD_MESSAGE,
            reply_markup=ReplyKeyboardMarkup(method_keyboard, resize_keyboard=True),
        )

    async def _handle_method_selection(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        text: str,
    ):
        """Handle optimization method selection."""
        # Handle email delivery button
        if text == BTN_EMAIL_DELIVERY:
            if self.email_flow_orchestrator:
                # Check health before starting email flow
                try:
                    from .health_checks import get_health_monitor

                    health_monitor = get_health_monitor()

                    # Check if Redis is healthy (required for email flow)
                    if not health_monitor.is_service_healthy("redis"):
                        await self._safe_reply(
                            update,
                            ERROR_REDIS_UNAVAILABLE,
                            reply_markup=ReplyKeyboardMarkup(
                                [[BTN_RESET]], resize_keyboard=True
                            ),
                        )
                        logger.warning(
                            f"email_flow_blocked_redis_unhealthy | user_id={user_id}"
                        )
                        return

                    # Check if SMTP is healthy - warn but allow to proceed with chat fallback
                    if not health_monitor.is_service_healthy("smtp"):
                        logger.warning(
                            f"email_flow_smtp_unhealthy_proceeding_with_fallback | user_id={user_id}"
                        )
                        # SMTP unhealthy, but we can still proceed with chat fallback
                        # The email flow orchestrator will handle the fallback
                        pass

                except Exception as e:
                    # Health monitor not available, log warning but proceed
                    logger.warning(
                        f"health_monitor_unavailable_proceeding | user_id={user_id} | error={e}"
                    )
                    pass

                try:
                    await self.email_flow_orchestrator.start_email_flow(
                        update, context, user_id
                    )
                except Exception as e:
                    logger.error(f"Email flow error for user {user_id}: {e}")
                    await self._safe_reply(
                        update, "❌ Email service error. Please try again later."
                    )
            else:
                await self._safe_reply(
                    update, "❌ Email service not available. Please try again later."
                )
            return

        method_handlers = {
            BTN_CRAFT: ("CRAFT", self.prompt_loader.craft_prompt),
            BTN_LYRA: (
                "LYRA Basic",
                self.prompt_loader.lyra_prompt,
                "BASIC using ChatGPT",
            ),
            BTN_LYRA_DETAIL: (
                "LYRA Detail",
                self.prompt_loader.lyra_prompt,
                "DETAILED using ChatGPT",
            ),
            BTN_GGL: ("GGL", self.prompt_loader.ggl_prompt),
        }

        if text not in method_handlers:
            # Invalid selection, show options again
            method_keyboard = list(SELECT_METHOD_KEYBOARD.keyboard)
            method_keyboard.append([BTN_RESET])
            await self._safe_reply(
                update,
                SELECT_METHOD_MESSAGE,
                reply_markup=ReplyKeyboardMarkup(method_keyboard, resize_keyboard=True),
            )
            return

        handler_data = method_handlers[text]
        method_name = handler_data[0]
        system_prompt = handler_data[1]
        additional_message = handler_data[2] if len(handler_data) > 2 else None

        await self._process_method_selection(
            update, user_id, method_name, system_prompt, additional_message
        )

    async def _process_method_selection(
        self,
        update: Update,
        user_id: int,
        method_name: str,
        system_prompt: str,
        additional_message: str = None,
    ):
        """Process the selected optimization method."""
        transcript = self.conversation_manager.get_transcript(user_id)

        # Add system prompt if not present
        if not transcript or transcript[0]["role"] != "system":
            transcript.insert(0, {"role": "system", "content": system_prompt})

        # Add additional message if specified (for LYRA variants)
        if additional_message:
            self.conversation_manager.append_message(
                user_id, "user", additional_message
            )

        self.conversation_manager.set_waiting_for_method(user_id, False)
        self.conversation_manager.set_current_method(user_id, method_name)

        # Log method selection
        self._log_method_selection(user_id, method_name)

        # Send processing message
        processing_method = method_name.lower().replace(" ", "_")
        try:
            await update.message.reply_text(
                get_processing_message(processing_method), parse_mode="Markdown"
            )
        except Exception as e:
            # Fallback without Markdown if parsing fails
            logger.warning(f"Markdown parsing failed: {e}")
            await update.message.reply_text(get_processing_message(processing_method))

        # Process with LLM
        await self._process_with_llm(update, user_id, method_name)

    async def _handle_conversation_turn(self, update: Update, user_id: int, text: str):
        """Handle multi-turn conversation."""
        self.conversation_manager.append_message(user_id, "user", text)

        method_name = self.conversation_manager.get_current_method(user_id)
        await self._process_with_llm(update, user_id, method_name)

    async def _handle_followup_choice(self, update: Update, user_id: int, text: str):
        """Handle follow-up choice (YES/NO) from user."""
        if text == BTN_NO:
            # User declined follow-up questions
            # Send reset confirmation message
            await self._safe_reply(
                update,
                RESET_CONFIRMATION,
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True),
            )

            # Reset state to prompt input ready
            self.state_manager.set_waiting_for_followup_choice(user_id, False)
            self.state_manager.set_waiting_for_prompt(user_id, True)
            self.state_manager.set_improved_prompt_cache(user_id, None)  # Clear cache
            self.conversation_manager.reset(user_id)

            logger.info(f"followup_declined | user_id={user_id}")

        elif text == BTN_YES:
            # User accepted follow-up questions
            # Get cached improved prompt
            improved_prompt = self.state_manager.get_improved_prompt_cache(user_id)
            if not improved_prompt:
                # Fallback if cache is missing - should not happen in normal flow
                logger.warning(f"followup_accepted_no_cache | user_id={user_id}")
                await self._safe_reply(
                    update,
                    RESET_CONFIRMATION,
                    parse_mode="Markdown",
                    reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True),
                )
                self.reset_user_state(user_id)
                return

            # Send instruction message first
            await self._safe_reply(
                update,
                FOLLOWUP_PROMPT_INPUT_MESSAGE,
                parse_mode="Markdown",
            )

            # Send ForceReply with improved prompt wrapped in code blocks
            await self._safe_reply(
                update,
                f"```\n{improved_prompt}\n```",
                parse_mode="Markdown",
                reply_markup=create_prompt_input_reply(improved_prompt),
            )

            # Update state to wait for prompt input instead of starting conversation immediately
            self.state_manager.set_waiting_for_followup_choice(user_id, False)
            self.state_manager.set_waiting_for_followup_prompt_input(user_id, True)

            logger.info(f"followup_accepted_prompt_input | user_id={user_id}")

        else:
            # Invalid choice, show options again
            # This should not happen with proper keyboard, but handle gracefully
            logger.warning(f"invalid_followup_choice | user_id={user_id} | text={text}")
            # Keep the same state and don't respond - user should use buttons

    async def _handle_followup_prompt_input(
        self, update: Update, user_id: int, text: str
    ):
        """Handle user prompt input from ForceReply during follow-up flow."""
        # The user has sent their prompt (modified or unmodified) from the input area
        # This prompt will be used to start the follow-up conversation

        logger.info(f"followup_prompt_input | user_id={user_id} | length={len(text)}")

        # Start follow-up conversation with the received prompt
        self.conversation_manager.start_followup_conversation(user_id, text)

        # Reset token counters to start new accumulation session for follow-up only
        # This ensures we only track tokens used during the follow-up conversation
        self.conversation_manager.reset_token_totals(user_id)

        # Update state transitions
        self.state_manager.set_waiting_for_followup_prompt_input(user_id, False)
        self.state_manager.set_in_followup_conversation(user_id, True)

        logger.info(f"followup_conversation_started | user_id={user_id}")

        # Send initial request to LLM to start asking questions
        await self._process_with_llm(update, user_id, "FOLLOWUP")

    async def _handle_followup_conversation(
        self, update: Update, user_id: int, text: str
    ):
        """Handle follow-up conversation during question-answer phase."""

        # Check if user clicked the generate prompt button
        if text == BTN_GENERATE_PROMPT:
            await self._process_followup_generation(update, user_id)
            return

        # Add user response to conversation history
        self.conversation_manager.append_message(user_id, "user", text)

        logger.info(f"followup_user_response | user_id={user_id} | length={len(text)}")

        # Send user response to LLM and get next question or refined prompt
        try:
            await self._process_followup_llm_request(update, user_id)

        except Exception as e:
            await self._handle_followup_error(update, user_id, e, "conversation")

    async def _process_followup_generation(self, update: Update, user_id: int):
        """Handle generate prompt button click during follow-up conversation."""
        # Send the generate signal to LLM
        self.conversation_manager.append_message(user_id, "user", "<GENERATE_PROMPT>")

        logger.info(f"followup_generate_requested | user_id={user_id}")

        try:
            await self._process_followup_llm_request(
                update, user_id, expect_refined_prompt=True
            )

        except Exception as e:
            await self._handle_followup_error(update, user_id, e, "generation")

    async def _complete_followup_conversation(
        self, update: Update, user_id: int, refined_prompt: str
    ):
        """Complete the follow-up conversation by sending refined prompt and resetting state."""
        # Send the refined prompt to user
        await self._safe_reply(
            update,
            refined_prompt,
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True),
        )

        # Send follow-up completion message
        await self._safe_reply(
            update,
            PROMPT_READY_FOLLOW_UP,
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True),
        )

        # Log conversation totals for follow-up
        # Use cached improved prompt as UserRequest for follow-up logging
        improved_prompt = self.state_manager.get_improved_prompt_cache(user_id)
        self._log_conversation_totals(
            user_id, "FOLLOWUP", refined_prompt, improved_prompt
        )

        # Reset state to prompt input ready
        self.reset_user_state(user_id)

        logger.info(f"followup_completed | user_id={user_id}")

    async def _process_followup_llm_request(
        self, update: Update, user_id: int, expect_refined_prompt: bool = False
    ):
        """
        Process LLM request during follow-up conversation with comprehensive error handling.

        Args:
            update: Telegram update object
            user_id: User ID
            expect_refined_prompt: Whether we expect a refined prompt (for generation requests)
        """
        # Validate follow-up conversation state
        if not self._validate_followup_state(user_id):
            logger.warning(f"followup_invalid_state | user_id={user_id}")
            await self._recover_followup_state(update, user_id)
            return

        transcript = self.conversation_manager.get_transcript(user_id)

        # Validate transcript integrity
        # Validate transcript integrity
        if not self._validate_followup_transcript(transcript):
            logger.warning(f"followup_invalid_transcript | user_id={user_id}")
            await self._recover_followup_state(update, user_id)
            return

        try:
            raw_response = await self.llm_client.send_prompt(transcript)

            # Track token usage
            usage = self.llm_client.get_last_usage()
            self.conversation_manager.accumulate_token_usage(user_id, usage)

            # Add LLM response to conversation history
            self.conversation_manager.append_message(user_id, "assistant", raw_response)

            # Parse response with enhanced error handling
            parsed_response, is_refined_prompt = (
                self._parse_followup_response_with_fallback(raw_response, user_id)
            )

            if is_refined_prompt:
                # LLM provided refined prompt, complete the follow-up flow
                await self._complete_followup_conversation(
                    update, user_id, parsed_response
                )
            elif expect_refined_prompt:
                # We expected a refined prompt but didn't get one
                logger.warning(f"followup_expected_refined_prompt | user_id={user_id}")
                await self._handle_missing_refined_prompt(update, user_id)
            else:
                # LLM asked another question, continue conversation
                await self._safe_reply(
                    update,
                    parsed_response,
                    parse_mode="Markdown",
                    reply_markup=FOLLOWUP_CONVERSATION_KEYBOARD,
                )
                logger.info(f"followup_question_sent | user_id={user_id}")

        except Exception as e:
            # Re-raise to be handled by caller
            raise e

    async def _handle_followup_error(
        self, update: Update, user_id: int, error: Exception, context: str
    ):
        """
        Handle errors during follow-up conversations with appropriate fallback strategies.

        Args:
            update: Telegram update object
            user_id: User ID
            error: The exception that occurred
            context: Context where error occurred ('conversation', 'generation', etc.)
        """
        logger.error(
            f"followup_error | user_id={user_id} | context={context} | error={str(error)}",
            exc_info=True,
        )

        # Determine error type and appropriate response
        error_type = self._classify_followup_error(error)

        if error_type == "timeout":
            await self._handle_followup_timeout(update, user_id, context)
        elif error_type == "network":
            await self._handle_followup_network_error(update, user_id, context)
        elif error_type == "rate_limit":
            await self._handle_followup_rate_limit(update, user_id, context)
        elif error_type == "api_error":
            await self._handle_followup_api_error(update, user_id, context)
        else:
            # Generic error handling
            await self._handle_followup_generic_error(update, user_id, context)

    def _classify_followup_error(self, error: Exception) -> str:
        """
        Classify the type of error for appropriate handling.

        Args:
            error: The exception to classify

        Returns:
            Error type string ('timeout', 'network', 'rate_limit', 'api_error', 'generic')
        """
        error_str = str(error).lower()

        if "timeout" in error_str or "timed out" in error_str:
            return "timeout"
        elif "connection" in error_str or "network" in error_str:
            return "network"
        elif "rate limit" in error_str or "too many requests" in error_str:
            return "rate_limit"
        elif "api" in error_str and ("error" in error_str or "invalid" in error_str):
            return "api_error"
        else:
            return "generic"

    async def _handle_followup_timeout(
        self, update: Update, user_id: int, context: str
    ):
        """Handle timeout errors during follow-up conversations."""
        logger.info(
            f"followup_timeout_fallback | user_id={user_id} | context={context}"
        )

        # Try to fallback to cached improved prompt
        improved_prompt = self.state_manager.get_improved_prompt_cache(user_id)
        if improved_prompt:
            await self._safe_reply(
                update,
                "Время ожидания истекло. Используем исходный улучшенный промпт:",
                reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True),
            )
            await self._complete_followup_conversation(update, user_id, improved_prompt)
        else:
            await self._fallback_to_prompt_input(
                update,
                user_id,
                "Время ожидания истекло. Попробуйте начать с нового промпта.",
            )

    async def _handle_followup_network_error(
        self, update: Update, user_id: int, context: str
    ):
        """Handle network errors during follow-up conversations."""
        logger.info(
            f"followup_network_error_fallback | user_id={user_id} | context={context}"
        )

        improved_prompt = self.state_manager.get_improved_prompt_cache(user_id)
        if improved_prompt:
            await self._safe_reply(
                update,
                "Проблемы с сетью. Используем исходный улучшенный промпт:",
                reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True),
            )
            await self._complete_followup_conversation(update, user_id, improved_prompt)
        else:
            await self._fallback_to_prompt_input(
                update, user_id, "Проблемы с сетью. Попробуйте начать с нового промпта."
            )

    async def _handle_followup_rate_limit(
        self, update: Update, user_id: int, context: str
    ):
        """Handle rate limit errors during follow-up conversations."""
        logger.info(
            f"followup_rate_limit_fallback | user_id={user_id} | context={context}"
        )

        improved_prompt = self.state_manager.get_improved_prompt_cache(user_id)
        if improved_prompt:
            await self._safe_reply(
                update,
                "Превышен лимит запросов. Используем исходный улучшенный промпт:",
                reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True),
            )
            await self._complete_followup_conversation(update, user_id, improved_prompt)
        else:
            await self._fallback_to_prompt_input(
                update, user_id, "Превышен лимит запросов. Попробуйте позже."
            )

    async def _handle_followup_api_error(
        self, update: Update, user_id: int, context: str
    ):
        """Handle API errors during follow-up conversations."""
        logger.info(
            f"followup_api_error_fallback | user_id={user_id} | context={context}"
        )

        improved_prompt = self.state_manager.get_improved_prompt_cache(user_id)
        if improved_prompt:
            await self._safe_reply(
                update,
                "Ошибка API. Используем исходный улучшенный промпт:",
                reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True),
            )
            await self._complete_followup_conversation(update, user_id, improved_prompt)
        else:
            await self._fallback_to_prompt_input(
                update, user_id, "Ошибка API. Попробуйте начать с нового промпта."
            )

    async def _handle_followup_generic_error(
        self, update: Update, user_id: int, context: str
    ):
        """Handle generic errors during follow-up conversations."""
        logger.info(
            f"followup_generic_error_fallback | user_id={user_id} | context={context}"
        )

        improved_prompt = self.state_manager.get_improved_prompt_cache(user_id)
        if improved_prompt:
            await self._complete_followup_conversation(update, user_id, improved_prompt)
        else:
            await self._fallback_to_prompt_input(
                update, user_id, "Произошла ошибка. Попробуйте начать с нового промпта."
            )

    async def _handle_missing_refined_prompt(self, update: Update, user_id: int):
        """Handle cases where we expected a refined prompt but didn't get one."""
        logger.warning(f"followup_missing_refined_prompt | user_id={user_id}")

        improved_prompt = self.state_manager.get_improved_prompt_cache(user_id)
        if improved_prompt:
            await self._safe_reply(
                update,
                "Не удалось получить улучшенный промпт. Используем исходный:",
                reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True),
            )
            await self._complete_followup_conversation(update, user_id, improved_prompt)
        else:
            await self._fallback_to_prompt_input(
                update,
                user_id,
                "Не удалось сгенерировать улучшенный промпт. Попробуйте начать заново.",
            )

    async def _fallback_to_prompt_input(
        self, update: Update, user_id: int, message: str
    ):
        """Fallback to prompt input state with error message."""
        await self._safe_reply(
            update,
            message,
            reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True),
        )
        self.reset_user_state(user_id)

    def _validate_followup_state(self, user_id: int) -> bool:
        """
        Validate that the user is in a valid follow-up conversation state.

        Args:
            user_id: User ID to validate

        Returns:
            True if state is valid, False otherwise
        """
        try:
            user_state = self.state_manager.get_user_state(user_id)

            # Check if user is supposed to be in follow-up conversation
            if not user_state.in_followup_conversation:
                return False

            # Check if we have a cached improved prompt
            if not user_state.improved_prompt_cache:
                return False

            # Check if conversation manager thinks we're in follow-up
            if not self.conversation_manager.is_in_followup_conversation(user_id):
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating follow-up state for user {user_id}: {e}")
            return False

    def _validate_followup_transcript(self, transcript: list) -> bool:
        """
        Validate that the follow-up conversation transcript is in a valid state.

        Args:
            transcript: Conversation transcript to validate

        Returns:
            True if transcript is valid, False otherwise
        """
        try:
            # Must have at least system prompt and improved prompt
            if len(transcript) < 2:
                return False

            # First message should be system prompt
            if transcript[0].get("role") != "system":
                return False

            # Should contain follow-up system prompt indicators
            system_content = transcript[0].get("content", "").lower()
            if "промпт-инжинирингу" not in system_content:
                return False

            # Second message should be user message (improved prompt)
            if transcript[1].get("role") != "user":
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating follow-up transcript: {e}")
            return False

    async def _recover_followup_state(self, update: Update, user_id: int):
        """
        Attempt to recover from corrupted follow-up conversation state.

        Args:
            update: Telegram update object
            user_id: User ID to recover
        """
        logger.info(f"followup_state_recovery | user_id={user_id}")

        try:
            # Try to get cached improved prompt
            improved_prompt = self.state_manager.get_improved_prompt_cache(user_id)

            if improved_prompt:
                # We have a cached prompt, offer it to the user
                await self._safe_reply(
                    update,
                    "Восстанавливаем состояние диалога. Используем ваш улучшенный промпт:",
                    reply_markup=ReplyKeyboardMarkup(
                        [[BTN_RESET]], resize_keyboard=True
                    ),
                )
                await self._complete_followup_conversation(
                    update, user_id, improved_prompt
                )
            else:
                # No cached prompt, reset to prompt input
                await self._fallback_to_prompt_input(
                    update,
                    user_id,
                    "Состояние диалога повреждено. Начните с нового промпта.",
                )

        except Exception as e:
            logger.error(
                f"Error during follow-up state recovery for user {user_id}: {e}"
            )
            # Complete fallback
            await self._fallback_to_prompt_input(
                update,
                user_id,
                "Не удалось восстановить состояние. Начните с нового промпта.",
            )

    def _parse_followup_response_with_fallback(
        self, response: str, user_id: int
    ) -> tuple[str, bool]:
        """
        Parse follow-up LLM response with enhanced error handling and fallback strategies.

        Args:
            response: Raw LLM response
            user_id: User ID for logging

        Returns:
            tuple: (parsed_content, is_refined_prompt)
        """
        try:
            # Try standard parsing first
            parsed_response, is_refined_prompt = parse_followup_response(response)

            # Check for empty refined prompt tags (when parse_followup_response returns original response but tags exist)
            if not is_refined_prompt and "<REFINED_PROMPT>" in response.upper():
                # This means parse_followup_response found empty content and returned original response
                logger.warning(f"followup_empty_refined_prompt | user_id={user_id}")
                return self._fallback_parse_refined_prompt(response, user_id)

            return parsed_response, is_refined_prompt

        except Exception as e:
            logger.error(f"followup_parse_error | user_id={user_id} | error={str(e)}")

            # On parse error, return original response as fallback
            return response.strip(), False

    def _fallback_parse_refined_prompt(
        self, response: str, user_id: int
    ) -> tuple[str, bool]:
        """
        Fallback parsing strategy for malformed refined prompt responses.

        Args:
            response: Raw LLM response
            user_id: User ID for logging

        Returns:
            tuple: (parsed_content, is_refined_prompt)
        """
        logger.info(f"followup_fallback_parse | user_id={user_id}")

        try:
            # Try to extract content after the opening tag
            upper_response = response.upper()
            start_idx = upper_response.find("<REFINED_PROMPT>")

            if start_idx != -1:
                content_start = start_idx + len("<REFINED_PROMPT>")
                content = response[content_start:].strip()

                # Remove any closing tags we can find
                closing_patterns = [
                    "</REFINED_PROMPT>",
                    "<END REFINED_PROMPT>",
                    "<END_REFINED_PROMPT>",
                    "[END REFINED_PROMPT]",
                    "[/REFINED_PROMPT]",
                    "<REFINED_PROMPT_END>",
                    "<END>",
                ]

                for pattern in closing_patterns:
                    if pattern.upper() in content.upper():
                        end_idx = content.upper().find(pattern.upper())
                        content = content[:end_idx].strip()
                        break

                if content:
                    return content, True

            # If we still don't have content, use the whole response
            logger.warning(f"followup_fallback_parse_failed | user_id={user_id}")
            return response.strip(), False

        except Exception as e:
            logger.error(
                f"followup_fallback_parse_error | user_id={user_id} | error={str(e)}"
            )
            return response.strip(), False

    async def _process_with_llm(self, update: Update, user_id: int, method_name: str):
        """Process conversation with LLM and handle response."""
        try:
            transcript = self.conversation_manager.get_transcript(user_id)
            raw_response = await self.llm_client.send_prompt(transcript)

            # Track token usage
            usage = self.llm_client.get_last_usage()
            self.conversation_manager.accumulate_token_usage(user_id, usage)

            # Handle follow-up conversation differently
            if method_name == "FOLLOWUP":
                # This is the initial LLM response in follow-up conversation
                self.conversation_manager.append_message(
                    user_id, "assistant", raw_response
                )

                # Parse response to check if it's a refined prompt (shouldn't happen on first response)
                parsed_response, is_refined_prompt = parse_followup_response(
                    raw_response
                )

                if is_refined_prompt:
                    # Unexpected refined prompt on first response, complete flow
                    await self._complete_followup_conversation(
                        update, user_id, parsed_response
                    )
                else:
                    # Send LLM's initial questions with generate button
                    await self._safe_reply(
                        update,
                        parsed_response,
                        parse_mode="Markdown",
                        reply_markup=FOLLOWUP_CONVERSATION_KEYBOARD,
                    )

                    logger.info(f"followup_initial_questions | user_id={user_id}")

                return

            # Parse response for regular conversations
            response, is_question, is_improved_prompt = parse_llm_response(raw_response)
            self.conversation_manager.append_message(user_id, "assistant", raw_response)

            if is_improved_prompt:
                # Store the optimized prompt before formatting
                optimized_prompt = response

                # Send the optimized prompt immediately
                await self._safe_reply(
                    update,
                    optimized_prompt,
                    parse_mode="Markdown",
                    reply_markup=ReplyKeyboardMarkup(
                        [[BTN_RESET]], resize_keyboard=True
                    ),
                )

                # Cache the improved prompt for potential follow-up use
                self.state_manager.set_improved_prompt_cache(user_id, optimized_prompt)

                # Log conversation totals for initial optimization phase
                # This logs tokens with initial prompt as UserRequest and optimized prompt as Answer
                self._log_conversation_totals(user_id, method_name, optimized_prompt)

                # Send follow-up offer message with YES/NO buttons
                await self._safe_reply(
                    update,
                    FOLLOWUP_OFFER_MESSAGE,
                    parse_mode="Markdown",
                    reply_markup=FOLLOWUP_CHOICE_KEYBOARD,
                )

                # Reset conversation but set up for follow-up choice
                self.conversation_manager.reset_to_followup_ready(user_id)
                self.state_manager.set_waiting_for_followup_choice(user_id, True)
                self.state_manager.set_waiting_for_prompt(user_id, False)

                return  # Exit early since we've handled the improved prompt case

            await self._safe_reply(
                update,
                response,
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True),
            )

        except Exception as e:
            logger.error(f"Error processing LLM request: {e}", exc_info=True)
            logger.error(
                f"error | stage={method_name} | user_id={user_id} | error={str(e)}"
            )

            error_msg = f"Ошибка: {e}"
            await self._safe_reply(
                update,
                error_msg,
                reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True),
            )

    def _log_method_selection(self, user_id: int, method_name: str):
        """Log method selection to file only."""
        logger.info(f"method_selected | user_id={user_id} | method={method_name}")

    def _log_conversation_totals(
        self,
        user_id: int,
        method_name: str,
        answer_text: str = None,
        user_request: str = None,
    ):
        """Log conversation totals to sheets and reset token counters after successful logging."""
        try:
            usage_totals = self.conversation_manager.get_token_totals(user_id)
            if not usage_totals or all(v == 0 for v in usage_totals.values()):
                return

            # Use provided user_request or fall back to stored user prompt
            request_text = (
                user_request or self.conversation_manager.get_user_prompt(user_id) or ""
            )

            payload = {
                "BotID": self.config.bot_id or "UNKNOWN",
                "TelegramID": user_id,
                "LLM": f"{self.config.llm_backend}:{self.config.model_name}",
                "OptimizationModel": method_name,
                "UserRequest": request_text,
                "Answer": answer_text or "",
                **usage_totals,
            }
            self.log_sheets("conversation_totals", payload)

            # Reset token totals after successful logging to prevent double-counting
            self.conversation_manager.reset_token_totals(user_id)

        except Exception as e:
            logger.error(f"Failed to log conversation totals: {e}", exc_info=True)

    async def _safe_reply(self, update: Update, text: str, **kwargs) -> bool:
        """Safely send a reply with error handling and length limits."""
        try:
            await self._send_message_with_retry(update, text, **kwargs)
            return True
        except (RetryError, Exception) as e:
            # Handle both RetryError (when tenacity gives up) and other exceptions
            if isinstance(e, RetryError):
                logger.error(
                    f"Failed to send message after all retries: {e.last_attempt.exception()}"
                )
            else:
                logger.error(f"Failed to send message: {e}")
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception(lambda e: _is_network_error(e)),
        before_sleep=lambda retry_state: logger.warning(
            f"Network error sending message, retrying (attempt {retry_state.attempt_number}): {retry_state.outcome.exception()}"
        ),
        reraise=True,
    )
    async def _send_message_with_retry(self, update: Update, text: str, **kwargs):
        """Send message with retry logic using tenacity."""
        MAX_MESSAGE_LENGTH = 4096

        if len(text) > MAX_MESSAGE_LENGTH:
            # Log message splitting
            user_id = update.effective_user.id
            num_chunks = (len(text) + MAX_MESSAGE_LENGTH - 1) // MAX_MESSAGE_LENGTH
            logger.info(
                f"message_split | user_id={user_id} | original_length={len(text)} | chunks={num_chunks}"
            )

            # Split long messages
            for i in range(0, len(text), MAX_MESSAGE_LENGTH):
                chunk = text[i : i + MAX_MESSAGE_LENGTH]
                chunk_num = (i // MAX_MESSAGE_LENGTH) + 1

                try:
                    await update.message.reply_text(chunk, **kwargs)
                    logger.debug(
                        f"message_chunk_sent | user_id={user_id} | chunk={chunk_num}/{num_chunks}"
                    )
                except Exception as e:
                    # If it's a Markdown parsing error, try without parse_mode
                    if (
                        "parse entities" in str(e).lower()
                        or "markdown" in str(e).lower()
                    ):
                        kwargs_no_parse = {
                            k: v for k, v in kwargs.items() if k != "parse_mode"
                        }
                        await update.message.reply_text(chunk, **kwargs_no_parse)
                        logger.info(
                            f"message_chunk_sent_no_markdown | user_id={user_id} | chunk={chunk_num}/{num_chunks}"
                        )
                    else:
                        # Re-raise for tenacity to handle
                        raise e

                # Only use special formatting and reply markup for first message
                kwargs.pop("parse_mode", None)
                kwargs.pop("reply_markup", None)
        else:
            try:
                await update.message.reply_text(text, **kwargs)
            except Exception as e:
                # If it's a Markdown parsing error, try without parse_mode
                if "parse entities" in str(e).lower() or "markdown" in str(e).lower():
                    kwargs_no_parse = {
                        k: v for k, v in kwargs.items() if k != "parse_mode"
                    }
                    await update.message.reply_text(text, **kwargs_no_parse)
                    logger.info("Message sent successfully without Markdown parsing")
                else:
                    # Re-raise for tenacity to handle
                    raise e
