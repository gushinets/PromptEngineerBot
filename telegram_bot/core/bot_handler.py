"""
Telegram bot message handlers and core logic.
"""

import logging

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes
from tenacity import (
    RetryError,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from telegram_bot.dependencies import get_container
from telegram_bot.flows.email_flow import get_email_flow_orchestrator
from telegram_bot.services.llm.base import LLMClientBase
from telegram_bot.services.session_service import OptimizationMethod
from telegram_bot.services.user_tracking import get_user_tracking_service
from telegram_bot.utils.config import BotConfig
from telegram_bot.utils.messages import (
    BTN_CRAFT,
    BTN_EMAIL_DELIVERY,
    BTN_GENERATE_PROMPT,
    BTN_GGL,
    BTN_LYRA,
    BTN_NO,
    BTN_POST_OPTIMIZATION_EMAIL,
    BTN_RESET,
    BTN_YES,
    ERROR_EMAIL_INPUT_FAILED,
    ERROR_EMAIL_SERVICE_ERROR,
    ERROR_EMAIL_SERVICE_UNAVAILABLE,
    ERROR_GENERIC,
    ERROR_OTP_VERIFICATION_FAILED,
    ERROR_PROMPT_GENERATION_FAILED,
    ERROR_PROMPT_RETRIEVAL_FALLBACK,
    ERROR_REDIS_UNAVAILABLE,
    ERROR_STATE_CORRUPTED_RESTART,
    ERROR_STATE_RECOVERY_FAILED,
    ERROR_STATE_RECOVERY_SUCCESS,
    FOLLOWUP_API_ERROR_FALLBACK,
    FOLLOWUP_API_ERROR_RESTART,
    FOLLOWUP_CHOICE_KEYBOARD,
    FOLLOWUP_CONVERSATION_KEYBOARD,
    FOLLOWUP_DECLINED_MESSAGE,
    FOLLOWUP_GENERIC_ERROR_RESTART,
    FOLLOWUP_NETWORK_FALLBACK,
    FOLLOWUP_NETWORK_RESTART,
    FOLLOWUP_OFFER_MESSAGE,
    FOLLOWUP_RATE_LIMIT_FALLBACK,
    FOLLOWUP_RATE_LIMIT_RESTART,
    FOLLOWUP_TIMEOUT_FALLBACK,
    FOLLOWUP_TIMEOUT_RESTART,
    POST_FOLLOWUP_COMPLETION_KEYBOARD,
    POST_FOLLOWUP_DECLINE_KEYBOARD,
    PROMPT_READY_FOLLOW_UP,
    RESET_CONFIRMATION,
    SELECT_METHOD_KEYBOARD,
    SELECT_METHOD_MESSAGE,
    SUPPORT_KEYBOARD,
    SYSTEM_FOLLOWUP_PROMPT_INDICATOR,
    WELCOME_MESSAGE_1,
    WELCOME_MESSAGE_2,
    get_processing_message,
    parse_followup_response,
    parse_llm_response,
)


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

    def __init__(self, config: BotConfig, llm_client: LLMClientBase, sheets_logger_func=None):
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

        # Initialize user tracking service if available (Requirement 7.1)
        try:
            self.user_tracking_service = get_user_tracking_service()
        except RuntimeError:
            # User tracking service not initialized - will be set later if tracking is enabled
            self.user_tracking_service = None

        # Initialize session service for session tracking if database is available
        try:
            self.session_service = container.get_session_service()
        except RuntimeError:
            # Database not initialized - session tracking will be disabled
            self.session_service = None

    def set_email_flow_orchestrator(self, orchestrator):
        """Set the email flow orchestrator after initialization."""
        self.email_flow_orchestrator = orchestrator

    def set_user_tracking_service(self, service):
        """Set the user tracking service after initialization."""
        self.user_tracking_service = service

    def set_session_service(self, service):
        """Set the session service after initialization."""
        self.session_service = service

    def reset_user_state(
        self,
        user_id: int,
        preserve_post_optimization: bool = False,
        skip_session_reset: bool = False,
    ):
        """
        Reset the user's state and conversation history.

        Args:
            user_id: User ID to reset
            preserve_post_optimization: If True, preserve post_optimization_result for email button
            skip_session_reset: If True, skip marking session as unsuccessful (used when session
                               is already completed successfully, e.g., after followup completion)
        """
        # Reset current session as unsuccessful before clearing state (Requirements 3.1)
        # This must happen BEFORE clearing the session ID from state
        # Skip if session was already completed successfully (e.g., after followup)
        if not skip_session_reset:
            self._reset_current_session(user_id)

        self.state_manager.set_waiting_for_prompt(user_id, True)
        self.state_manager.set_last_interaction(user_id, None)
        # Reset follow-up states
        self.state_manager.set_waiting_for_followup_choice(user_id, False)
        self.state_manager.set_in_followup_conversation(user_id, False)
        self.state_manager.set_improved_prompt_cache(user_id, None)
        self.state_manager.set_cached_method_name(user_id, None)
        # Reset email states
        self.state_manager.set_waiting_for_email_input(user_id, False)
        self.state_manager.set_waiting_for_otp_input(user_id, False)
        self.state_manager.set_email_flow_data(user_id, None)
        # Reset post-optimization result (unless we want to preserve it)
        if not preserve_post_optimization:
            self.state_manager.set_post_optimization_result(user_id, None)
            # Reset session tracking state only when not preserving post-optimization
            # Session ID should remain available for post-completion email tracking (Requirements 7.4)
            self.state_manager.set_current_session_id(user_id, None)
        self.conversation_manager.reset(user_id)

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command or New Prompt button."""
        user_id = update.effective_user.id

        # Track user interaction early in /start processing (Requirement 7.1)
        # This creates user on first interaction or updates last_interaction_at
        if self.user_tracking_service:
            tracked_user, is_first_time = self.user_tracking_service.track_user_interaction(
                user_id, update.effective_user
            )
            # Handle None return gracefully - database error case (Requirement 7.3)
            # Continue processing even if tracking fails
            if tracked_user is None:
                logger.warning(
                    f"User tracking returned None for user_id={user_id} in handle_start, continuing with request"
                )

        # Reset user state without logging tokens
        # Token logging should only happen when optimized prompts are generated
        self.reset_user_state(user_id)

        # Send welcome message 1 (introduction)
        await self._safe_reply(
            update,
            WELCOME_MESSAGE_1,
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True),
        )

        # Send welcome message 2 (instructions) with support button
        await self._safe_reply(
            update,
            WELCOME_MESSAGE_2,
            parse_mode="Markdown",
            reply_markup=SUPPORT_KEYBOARD,
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages from users."""
        user_id = update.effective_user.id
        text = update.message.text

        # Track user interaction early in message processing (Requirement 7.1)
        # This creates user on first interaction or updates last_interaction_at
        if self.user_tracking_service:
            tracked_user, is_first_time = self.user_tracking_service.track_user_interaction(
                user_id, update.effective_user
            )
            # Handle None return gracefully - database error case (Requirement 7.3)
            # Continue processing even if tracking fails
            if tracked_user is None:
                logger.warning(
                    f"User tracking returned None for user_id={user_id}, continuing with request"
                )

        user_state = self.state_manager.get_user_state(user_id)

        # Reset button always resets conversation
        if text == BTN_RESET:
            await self.handle_start(update, context)
            return

        # Handle post-optimization email button
        if text == BTN_POST_OPTIMIZATION_EMAIL:
            await self._handle_post_optimization_email(update, context, user_id)
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
                    await self._safe_reply(update, ERROR_EMAIL_INPUT_FAILED)
            else:
                await self._safe_reply(update, ERROR_EMAIL_SERVICE_UNAVAILABLE)
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
                    await self._safe_reply(update, ERROR_OTP_VERIFICATION_FAILED)
            else:
                await self._safe_reply(update, ERROR_EMAIL_SERVICE_UNAVAILABLE)
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
        # Clear any previous session_id before creating a new session (Requirements 1.7)
        self.state_manager.set_current_session_id(user_id, None)

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

        # Start session tracking immediately when user sends prompt (Requirements 1.1, 1.5, 1.6)
        # Session is created with optimization_method=None, to be set when user selects method
        await self._start_session_for_prompt(user_id, text)

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
                    from telegram_bot.utils.health_checks import get_health_monitor

                    health_monitor = get_health_monitor()

                    # Check if Redis is healthy (required for email flow)
                    if not health_monitor.is_service_healthy("redis"):
                        await self._safe_reply(
                            update,
                            ERROR_REDIS_UNAVAILABLE,
                            reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True),
                        )
                        logger.warning(f"email_flow_blocked_redis_unhealthy | user_id={user_id}")
                        return

                    # Check if SMTP is healthy - warn but allow to proceed with chat fallback
                    if not health_monitor.is_service_healthy("smtp"):
                        logger.warning(
                            f"email_flow_smtp_unhealthy_proceeding_with_fallback | user_id={user_id}"
                        )
                        # SMTP unhealthy, but we can still proceed with chat fallback
                        # The email flow orchestrator will handle the fallback

                except Exception as e:
                    # Health monitor not available, log warning but proceed
                    logger.warning(
                        f"health_monitor_unavailable_proceeding | user_id={user_id} | error={e}"
                    )

                try:
                    await self.email_flow_orchestrator.start_email_flow(update, context, user_id)
                except Exception as e:
                    logger.error(f"Email flow error for user {user_id}: {e}")
                    await self._safe_reply(update, ERROR_EMAIL_SERVICE_ERROR)
            else:
                await self._safe_reply(update, ERROR_EMAIL_SERVICE_UNAVAILABLE)
            return

        method_handlers = {
            BTN_CRAFT: ("CRAFT", self.prompt_loader.craft_prompt),
            BTN_LYRA: (
                "LYRA Basic",
                self.prompt_loader.lyra_prompt,
                "BASIC using ChatGPT",
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
            self.conversation_manager.append_message(user_id, "user", additional_message)

        self.conversation_manager.set_waiting_for_method(user_id, False)
        self.conversation_manager.set_current_method(user_id, method_name)

        # Log method selection
        self._log_method_selection(user_id, method_name)

        # Update session with selected optimization method (Requirements 6.1)
        # Session was already created in _handle_prompt_input, now we set the method
        self._set_session_optimization_method(user_id, method_name)

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

        # Track user message in session (Requirements 10.1)
        self._track_session_message(user_id, "user", text)

        method_name = self.conversation_manager.get_current_method(user_id)
        await self._process_with_llm(update, user_id, method_name)

    async def _handle_post_optimization_email(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int
    ):
        """Handle post-optimization email button click."""
        if self.email_flow_orchestrator:
            try:
                # Check health before starting email flow
                from telegram_bot.utils.health_checks import get_health_monitor

                health_monitor = get_health_monitor()

                # Check if Redis is healthy (required for email flow)
                if not health_monitor.is_service_healthy("redis"):
                    await self._safe_reply(
                        update,
                        ERROR_REDIS_UNAVAILABLE,
                        reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True),
                    )
                    logger.warning(
                        f"post_optimization_email_blocked_redis_unhealthy | user_id={user_id}"
                    )
                    return

                # Check if SMTP is healthy - warn but allow to proceed with chat fallback
                if not health_monitor.is_service_healthy("smtp"):
                    logger.warning(
                        f"post_optimization_email_smtp_unhealthy_proceeding_with_fallback | user_id={user_id}"
                    )

            except Exception as e:
                # Health monitor not available, log warning but proceed
                logger.warning(
                    f"health_monitor_unavailable_proceeding_post_optimization | user_id={user_id} | error={e}"
                )

            try:
                # Start post-optimization email flow
                await self.email_flow_orchestrator.start_post_optimization_email_flow(
                    update, context, user_id
                )
            except Exception as e:
                logger.error(f"Post-optimization email flow error for user {user_id}: {e}")
                await self._safe_reply(update, ERROR_EMAIL_SERVICE_ERROR)
        else:
            await self._safe_reply(update, ERROR_EMAIL_SERVICE_UNAVAILABLE)

    async def _handle_followup_choice(self, update: Update, user_id: int, text: str):
        """Handle follow-up choice (YES/NO) from user."""
        if text == BTN_NO:
            # User declined follow-up questions
            # Preserve optimization result for post-optimization email button

            # Get the original prompt before any resets
            original_prompt = self.conversation_manager.get_user_prompt(user_id)

            # First check if we have a cached improved prompt (this should be available after optimization)
            improved_prompt = self.state_manager.get_improved_prompt_cache(user_id)

            # Get the cached method name (stored when the improved prompt was cached)
            cached_method = self.state_manager.get_cached_method_name(user_id)

            if improved_prompt:
                # We have an improved prompt from the initial optimization, use it
                # Use the cached method name, or fallback to "Optimization"
                method_name = cached_method if cached_method else "Optimization"

                self.state_manager.set_post_optimization_result(
                    user_id,
                    {
                        "type": "single_method",
                        "method_name": method_name,
                        "content": improved_prompt,
                        "original_prompt": original_prompt,
                    },
                )
                logger.info(
                    f"followup_declined_using_cached_prompt | user_id={user_id} | method={method_name} | content_length={len(improved_prompt)} | has_original={bool(original_prompt)}"
                )
            else:
                # This should not happen with proper state management
                # Log warning and continue without storing result
                logger.warning(
                    f"followup_declined_no_cached_prompt | user_id={user_id} | This indicates a state management issue"
                )

            # Send follow-up declined message with post-optimization email button
            await self._safe_reply(
                update,
                FOLLOWUP_DECLINED_MESSAGE,
                parse_mode="Markdown",
                reply_markup=POST_FOLLOWUP_DECLINE_KEYBOARD,
            )

            # Reset state to prompt input ready
            self.state_manager.set_waiting_for_followup_choice(user_id, False)
            self.state_manager.set_waiting_for_prompt(user_id, True)
            self.state_manager.set_improved_prompt_cache(user_id, None)  # Clear cache
            self.state_manager.set_cached_method_name(user_id, None)  # Clear cached method
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

            # Mark session as using followup optimization (Requirements 6.2)
            self._set_session_followup_used(user_id)

            # Start follow-up conversation immediately
            # Update state transitions to go directly from choice to conversation
            self.state_manager.set_waiting_for_followup_choice(user_id, False)

            # Start follow-up conversation using cached improved prompt
            self.conversation_manager.start_followup_conversation(user_id, improved_prompt)

            logger.info(f"followup_accepted | user_id={user_id}")

            # Send initial request to LLM to get first question
            try:
                await self._process_followup_llm_request(update, user_id)
            except Exception as e:
                await self._handle_followup_error(update, user_id, e, "conversation")

        else:
            # Invalid choice, show options again
            # This should not happen with proper keyboard, but handle gracefully
            logger.warning(f"invalid_followup_choice | user_id={user_id} | text={text}")
            # Keep the same state and don't respond - user should use buttons

    async def _handle_followup_conversation(self, update: Update, user_id: int, text: str):
        """Handle follow-up conversation during question-answer phase."""

        # Check if user clicked the generate prompt button
        if text == BTN_GENERATE_PROMPT:
            await self._process_followup_generation(update, user_id)
            return

        # Add user response to conversation history
        self.conversation_manager.append_message(user_id, "user", text)

        # Track user message in session (Requirements 10.1)
        self._track_session_message(user_id, "user", text)

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
            await self._process_followup_llm_request(update, user_id, expect_refined_prompt=True)

        except Exception as e:
            await self._handle_followup_error(update, user_id, e, "generation")

    async def _complete_followup_conversation(
        self, update: Update, user_id: int, refined_prompt: str
    ):
        """Complete the follow-up conversation by sending refined prompt and resetting state."""
        # Get original prompt before resetting
        original_prompt = self.conversation_manager.get_user_prompt(user_id)

        # Send the refined prompt to user
        await self._safe_reply(
            update,
            refined_prompt,
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True),
        )

        # Send follow-up completion message with post-optimization email button
        await self._safe_reply(
            update,
            PROMPT_READY_FOLLOW_UP,
            parse_mode="Markdown",
            reply_markup=POST_FOLLOWUP_COMPLETION_KEYBOARD,
        )

        # Log conversation totals for follow-up
        # Use cached improved prompt as UserRequest for follow-up logging
        improved_prompt = self.state_manager.get_improved_prompt_cache(user_id)
        self._log_conversation_totals(user_id, "FOLLOWUP", refined_prompt, improved_prompt)

        # Complete followup tracking - sets followup_finish_time and duration (Requirements 6a.2, 6a.3)
        self._complete_followup_tracking(user_id)

        # Complete session tracking - refined prompt delivered (Requirements 2.1)
        self._complete_current_session(user_id)

        # Preserve the refined prompt for post-optimization email button
        # Store it BEFORE resetting state
        self.state_manager.set_post_optimization_result(
            user_id,
            {
                "type": "follow_up",
                "method_name": "Follow-up Optimization",
                "content": refined_prompt,
                "original_prompt": original_prompt,
            },
        )

        logger.info(
            f"followup_completed_result_preserved | user_id={user_id} | content_length={len(refined_prompt)} | has_original={bool(original_prompt)}"
        )

        # Reset state to prompt input ready, but preserve post-optimization result
        # Skip session reset since we already completed the session successfully above
        self.reset_user_state(user_id, preserve_post_optimization=True, skip_session_reset=True)

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

            # Track token usage for conversation manager (existing behavior)
            usage = self.llm_client.get_last_usage()
            self.conversation_manager.accumulate_token_usage(user_id, usage)

            # Track token usage for session tracking (Requirements 5.2, 5.3)
            self._track_session_tokens(user_id, usage)

            # Add LLM response to conversation history
            self.conversation_manager.append_message(user_id, "assistant", raw_response)

            # Track LLM response in session (Requirements 10.2)
            self._track_session_message(user_id, "assistant", raw_response)

            # Parse response with enhanced error handling
            parsed_response, is_refined_prompt = self._parse_followup_response_with_fallback(
                raw_response, user_id
            )

            if is_refined_prompt:
                # LLM provided refined prompt, complete the follow-up flow
                await self._complete_followup_conversation(update, user_id, parsed_response)
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
            f"followup_error | user_id={user_id} | context={context} | error={error!s}",
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
        if "connection" in error_str or "network" in error_str:
            return "network"
        if "rate limit" in error_str or "too many requests" in error_str:
            return "rate_limit"
        if "api" in error_str and ("error" in error_str or "invalid" in error_str):
            return "api_error"
        return "generic"

    async def _handle_followup_timeout(self, update: Update, user_id: int, context: str):
        """Handle timeout errors during follow-up conversations."""
        logger.info(f"followup_timeout_fallback | user_id={user_id} | context={context}")

        # Try to fallback to cached improved prompt
        improved_prompt = self.state_manager.get_improved_prompt_cache(user_id)
        if improved_prompt:
            await self._safe_reply(
                update,
                FOLLOWUP_TIMEOUT_FALLBACK,
                reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True),
            )
            await self._complete_followup_conversation(update, user_id, improved_prompt)
        else:
            await self._fallback_to_prompt_input(
                update,
                user_id,
                FOLLOWUP_TIMEOUT_RESTART,
            )

    async def _handle_followup_network_error(self, update: Update, user_id: int, context: str):
        """Handle network errors during follow-up conversations."""
        logger.info(f"followup_network_error_fallback | user_id={user_id} | context={context}")

        improved_prompt = self.state_manager.get_improved_prompt_cache(user_id)
        if improved_prompt:
            await self._safe_reply(
                update,
                FOLLOWUP_NETWORK_FALLBACK,
                reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True),
            )
            await self._complete_followup_conversation(update, user_id, improved_prompt)
        else:
            await self._fallback_to_prompt_input(update, user_id, FOLLOWUP_NETWORK_RESTART)

    async def _handle_followup_rate_limit(self, update: Update, user_id: int, context: str):
        """Handle rate limit errors during follow-up conversations."""
        logger.info(f"followup_rate_limit_fallback | user_id={user_id} | context={context}")

        improved_prompt = self.state_manager.get_improved_prompt_cache(user_id)
        if improved_prompt:
            await self._safe_reply(
                update,
                FOLLOWUP_RATE_LIMIT_FALLBACK,
                reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True),
            )
            await self._complete_followup_conversation(update, user_id, improved_prompt)
        else:
            await self._fallback_to_prompt_input(update, user_id, FOLLOWUP_RATE_LIMIT_RESTART)

    async def _handle_followup_api_error(self, update: Update, user_id: int, context: str):
        """Handle API errors during follow-up conversations."""
        logger.info(f"followup_api_error_fallback | user_id={user_id} | context={context}")

        improved_prompt = self.state_manager.get_improved_prompt_cache(user_id)
        if improved_prompt:
            await self._safe_reply(
                update,
                FOLLOWUP_API_ERROR_FALLBACK,
                reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True),
            )
            await self._complete_followup_conversation(update, user_id, improved_prompt)
        else:
            await self._fallback_to_prompt_input(update, user_id, FOLLOWUP_API_ERROR_RESTART)

    async def _handle_followup_generic_error(self, update: Update, user_id: int, context: str):
        """Handle generic errors during follow-up conversations."""
        logger.info(f"followup_generic_error_fallback | user_id={user_id} | context={context}")

        improved_prompt = self.state_manager.get_improved_prompt_cache(user_id)
        if improved_prompt:
            await self._complete_followup_conversation(update, user_id, improved_prompt)
        else:
            await self._fallback_to_prompt_input(update, user_id, FOLLOWUP_GENERIC_ERROR_RESTART)

    async def _handle_missing_refined_prompt(self, update: Update, user_id: int):
        """Handle cases where we expected a refined prompt but didn't get one."""
        logger.warning(f"followup_missing_refined_prompt | user_id={user_id}")

        improved_prompt = self.state_manager.get_improved_prompt_cache(user_id)
        if improved_prompt:
            await self._safe_reply(
                update,
                ERROR_PROMPT_RETRIEVAL_FALLBACK,
                reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True),
            )
            await self._complete_followup_conversation(update, user_id, improved_prompt)
        else:
            await self._fallback_to_prompt_input(
                update,
                user_id,
                ERROR_PROMPT_GENERATION_FAILED,
            )

    async def _fallback_to_prompt_input(self, update: Update, user_id: int, message: str):
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
            if not self.state_manager.get_improved_prompt_cache(user_id):
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
            if SYSTEM_FOLLOWUP_PROMPT_INDICATOR not in system_content:
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
                    ERROR_STATE_RECOVERY_SUCCESS,
                    reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True),
                )
                await self._complete_followup_conversation(update, user_id, improved_prompt)
            else:
                # No cached prompt, reset to prompt input
                await self._fallback_to_prompt_input(
                    update,
                    user_id,
                    ERROR_STATE_CORRUPTED_RESTART,
                )

        except Exception as e:
            logger.error(f"Error during follow-up state recovery for user {user_id}: {e}")
            # Complete fallback
            await self._fallback_to_prompt_input(
                update,
                user_id,
                ERROR_STATE_RECOVERY_FAILED,
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
            logger.error(f"followup_parse_error | user_id={user_id} | error={e!s}")

            # On parse error, return original response as fallback
            return response.strip(), False

    def _fallback_parse_refined_prompt(self, response: str, user_id: int) -> tuple[str, bool]:
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
            logger.error(f"followup_fallback_parse_error | user_id={user_id} | error={e!s}")
            return response.strip(), False

    async def _process_with_llm(self, update: Update, user_id: int, method_name: str):
        """Process conversation with LLM and handle response."""
        try:
            transcript = self.conversation_manager.get_transcript(user_id)
            raw_response = await self.llm_client.send_prompt(transcript)

            # Track token usage for conversation manager (existing behavior)
            usage = self.llm_client.get_last_usage()
            self.conversation_manager.accumulate_token_usage(user_id, usage)

            # Track token usage for session tracking (Requirements 5.2, 5.3)
            self._track_session_tokens(user_id, usage)

            # Handle follow-up conversation differently
            if method_name == "FOLLOWUP":
                # This is the initial LLM response in follow-up conversation
                self.conversation_manager.append_message(user_id, "assistant", raw_response)

                # Track LLM response in session (Requirements 10.2)
                self._track_session_message(user_id, "assistant", raw_response)

                # Parse response to check if it's a refined prompt (shouldn't happen on first response)
                parsed_response, is_refined_prompt = parse_followup_response(raw_response)

                if is_refined_prompt:
                    # Unexpected refined prompt on first response, complete flow
                    await self._complete_followup_conversation(update, user_id, parsed_response)
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

            # Track LLM response in session (Requirements 10.2)
            self._track_session_message(user_id, "assistant", raw_response)

            if is_improved_prompt:
                # Store the optimized prompt before formatting
                optimized_prompt = response

                # Send the optimized prompt immediately
                await self._safe_reply(
                    update,
                    optimized_prompt,
                    parse_mode="Markdown",
                    reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True),
                )

                # Cache the improved prompt AND method name for potential follow-up use
                self.state_manager.set_improved_prompt_cache(user_id, optimized_prompt)
                self.state_manager.set_cached_method_name(user_id, method_name)

                # Log conversation totals for initial optimization phase
                # This logs tokens with initial prompt as UserRequest and optimized prompt as Answer
                self._log_conversation_totals(user_id, method_name, optimized_prompt)

                # Complete session tracking - improved prompt delivered (Requirements 2.1)
                self._complete_current_session(user_id)

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
            logger.error(f"error | stage={method_name} | user_id={user_id} | error={e!s}")

            await self._safe_reply(
                update,
                ERROR_GENERIC,
                reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True),
            )

    def _log_method_selection(self, user_id: int, method_name: str):
        """Log method selection to file only."""
        logger.info(f"method_selected | user_id={user_id} | method={method_name}")

    def _track_session_message(self, telegram_user_id: int, role: str, content: str):
        """
        Track a message in the current session's conversation history.

        This method adds a message to the session's conversation_history JSONB field.
        It follows graceful degradation - if session tracking fails, the user's
        experience is not affected.

        Args:
            telegram_user_id: Telegram user ID
            role: Message role - "user" or "assistant"
            content: Message content text

        Requirements: 10.1, 10.2
        """
        try:
            # Check if session service is available
            if not self.session_service:
                logger.debug(
                    f"session_message_tracking_skipped | user_id={telegram_user_id} | "
                    "reason=session_service_not_available"
                )
                return

            # Get current session ID from state
            session_id = self.state_manager.get_current_session_id(telegram_user_id)
            if session_id is None:
                logger.debug(
                    f"session_message_tracking_skipped | user_id={telegram_user_id} | "
                    "reason=no_active_session"
                )
                return

            # Add message to session
            result = self.session_service.add_message(
                session_id=session_id,
                role=role,
                content=content,
            )

            if result:
                logger.debug(
                    f"session_message_tracked | user_id={telegram_user_id} | "
                    f"session_id={session_id} | role={role} | content_length={len(content)}"
                )
            else:
                # Graceful degradation - log warning but continue
                logger.warning(
                    f"session_message_tracking_failed | user_id={telegram_user_id} | "
                    f"session_id={session_id} | role={role} | continuing_without_tracking"
                )

        except Exception as e:
            # Graceful degradation - session tracking failure should not block user
            logger.error(
                f"session_message_tracking_error | user_id={telegram_user_id} | "
                f"role={role} | error={e}",
                exc_info=True,
            )

    def _track_session_tokens(self, telegram_user_id: int, usage: dict | None):
        """
        Track token usage for the current session.

        This method adds token counts from an LLM interaction to the current session.
        It follows graceful degradation - if session tracking fails, the user's
        experience is not affected.

        When in followup mode, tokens are tracked separately using add_followup_tokens()
        to maintain separate metrics for the followup conversation phase.

        Args:
            telegram_user_id: Telegram user ID
            usage: Token usage dict with prompt_tokens and completion_tokens

        Requirements: 5.2, 5.3, 6a.4, 6a.5
        """
        try:
            # Check if session service is available
            if not self.session_service:
                logger.debug(
                    f"session_token_tracking_skipped | user_id={telegram_user_id} | "
                    "reason=session_service_not_available"
                )
                return

            # Get current session ID from state
            session_id = self.state_manager.get_current_session_id(telegram_user_id)
            if session_id is None:
                logger.debug(
                    f"session_token_tracking_skipped | user_id={telegram_user_id} | "
                    "reason=no_active_session"
                )
                return

            # Extract token counts from usage dict
            if not usage:
                logger.debug(
                    f"session_token_tracking_skipped | user_id={telegram_user_id} | "
                    f"session_id={session_id} | reason=no_usage_data"
                )
                return

            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)

            # Check if we're in followup mode to determine which token tracking method to use
            # Requirements 6a.4, 6a.5: Track followup tokens separately
            user_state = self.state_manager.get_user_state(telegram_user_id)
            is_in_followup = user_state.in_followup_conversation

            if is_in_followup:
                # Add tokens to followup tracking (Requirements 6a.4, 6a.5)
                result = self.session_service.add_followup_tokens(
                    session_id=session_id,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
                token_type = "followup"
            else:
                # Add tokens to main session tracking (Requirements 5.2, 5.3)
                result = self.session_service.add_tokens(
                    session_id=session_id,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
                token_type = "initial"

            if result:
                logger.debug(
                    f"session_tokens_tracked | user_id={telegram_user_id} | "
                    f"session_id={session_id} | type={token_type} | "
                    f"input={input_tokens} | output={output_tokens}"
                )
            else:
                # Graceful degradation - log warning but continue
                logger.warning(
                    f"session_token_tracking_failed | user_id={telegram_user_id} | "
                    f"session_id={session_id} | type={token_type} | continuing_without_tracking"
                )

        except Exception as e:
            # Graceful degradation - session tracking failure should not block user
            logger.error(
                f"session_token_tracking_error | user_id={telegram_user_id} | error={e}",
                exc_info=True,
            )

    def _complete_current_session(self, telegram_user_id: int):
        """
        Complete the current session when improved prompt is delivered.

        This method marks the current session as successful when the user receives
        their improved prompt. It follows graceful degradation - if session tracking
        fails, the user's experience is not affected.

        Args:
            telegram_user_id: Telegram user ID

        Requirements: 2.1
        """
        try:
            # Check if session service is available
            if not self.session_service:
                logger.debug(
                    f"session_complete_skipped | user_id={telegram_user_id} | "
                    "reason=session_service_not_available"
                )
                return

            # Get current session ID from state
            session_id = self.state_manager.get_current_session_id(telegram_user_id)
            if session_id is None:
                logger.debug(
                    f"session_complete_skipped | user_id={telegram_user_id} | "
                    "reason=no_active_session"
                )
                return

            # Complete the session
            result = self.session_service.complete_session(session_id)

            if result:
                logger.info(
                    f"session_completed | telegram_user_id={telegram_user_id} | "
                    f"session_id={session_id} | status=successful | "
                    f"duration={result.duration_seconds}s"
                )
                # NOTE: Do NOT clear session_id from state here
                # Session_id must remain available for post-completion tracking
                # (followup conversations and email events) - Requirements 6.2, 7.4
            else:
                # Session completion failed - graceful degradation, continue
                logger.warning(
                    f"session_complete_failed | telegram_user_id={telegram_user_id} | "
                    f"session_id={session_id} | continuing_without_completion"
                )

        except Exception as e:
            # Graceful degradation - session tracking failure should not block user
            logger.error(
                f"session_complete_error | telegram_user_id={telegram_user_id} | error={e}",
                exc_info=True,
            )

    def _reset_current_session(self, telegram_user_id: int):
        """
        Reset the current session as unsuccessful when user resets dialog.

        This method implements Layer 1 of terminal state protection.
        It checks if the session is already in a terminal state before
        calling the SessionService, providing clear logging and avoiding
        unnecessary operations.

        Sessions that are already in a terminal state (successful or unsuccessful)
        will NOT be modified. Only sessions with status="in_progress" can be reset.

        Args:
            telegram_user_id: Telegram user ID

        Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 5.1, 5.2, 5.3
        """
        try:
            # Check if session service is available
            if not self.session_service:
                logger.debug(
                    f"session_reset_skipped | user_id={telegram_user_id} | "
                    "reason=session_service_not_available"
                )
                return

            # Get current session ID from state
            session_id = self.state_manager.get_current_session_id(telegram_user_id)
            if session_id is None:
                logger.debug(
                    f"session_reset_skipped | user_id={telegram_user_id} | reason=no_active_session"
                )
                return

            # Layer 1 Protection: Check session status before reset (Requirement 2.1)
            session = self.session_service.get_session(session_id)
            if session is None:
                logger.warning(
                    f"session_reset_skipped | user_id={telegram_user_id} | "
                    f"session_id={session_id} | reason=session_not_found"
                )
                return

            # Skip reset if session is already in terminal state (Requirements 2.2, 2.3, 5.1)
            if session.status != "in_progress":
                logger.info(
                    f"session_reset_skipped | user_id={telegram_user_id} | "
                    f"session_id={session_id} | status={session.status} | "
                    "reason=already_terminal_state"
                )
                return

            # Session is in_progress, proceed with reset (Requirement 2.4)
            result = self.session_service.reset_session(session_id)

            if result:
                logger.info(
                    f"session_reset | telegram_user_id={telegram_user_id} | "
                    f"session_id={session_id} | status=unsuccessful | "
                    f"duration={result.duration_seconds}s | "
                    f"tokens={result.tokens_total}"
                )
                # Note: session ID will be cleared by reset_user_state after this method returns
            else:
                # Session reset failed - graceful degradation, continue
                logger.warning(
                    f"session_reset_failed | telegram_user_id={telegram_user_id} | "
                    f"session_id={session_id} | continuing_without_reset"
                )

        except Exception as e:
            # Graceful degradation - session tracking failure should not block user (Requirement 4.1)
            logger.error(
                f"session_reset_error | telegram_user_id={telegram_user_id} | error={e}",
                exc_info=True,
            )

    def _set_session_followup_used(self, telegram_user_id: int):
        """
        Mark that FOLLOWUP optimization was used in the current session.

        This method sets the used_followup flag to True when the user opts for
        the secondary FOLLOWUP optimization phase. It follows graceful degradation -
        if session tracking fails, the user's experience is not affected.

        Args:
            telegram_user_id: Telegram user ID

        Requirements: 6.2
        """
        try:
            # Check if session service is available
            if not self.session_service:
                logger.debug(
                    f"session_followup_skipped | user_id={telegram_user_id} | "
                    "reason=session_service_not_available"
                )
                return

            # Get current session ID from state
            session_id = self.state_manager.get_current_session_id(telegram_user_id)
            if session_id is None:
                logger.debug(
                    f"session_followup_skipped | user_id={telegram_user_id} | "
                    "reason=no_active_session"
                )
                return

            # Start followup tracking (sets used_followup=True and followup_start_time)
            result = self.session_service.start_followup(session_id)

            if result:
                followup_time = (
                    result.followup_start_time.isoformat() if result.followup_start_time else "None"
                )
                logger.info(
                    f"session_followup_started | telegram_user_id={telegram_user_id} | "
                    f"session_id={session_id} | used_followup=True | "
                    f"followup_start_time={followup_time}"
                )
            else:
                # Starting followup failed - graceful degradation, continue
                logger.warning(
                    f"session_followup_start_failed | telegram_user_id={telegram_user_id} | "
                    f"session_id={session_id} | continuing_without_tracking"
                )

        except Exception as e:
            # Graceful degradation - session tracking failure should not block user
            logger.error(
                f"session_followup_error | telegram_user_id={telegram_user_id} | error={e}",
                exc_info=True,
            )

    def _complete_followup_tracking(self, telegram_user_id: int):
        """
        Complete followup conversation tracking for the current session.

        This method sets followup_finish_time and calculates followup_duration_seconds
        when the followup conversation completes. It follows graceful degradation -
        if session tracking fails, the user's experience is not affected.

        Args:
            telegram_user_id: Telegram user ID

        Requirements: 6a.2, 6a.3
        """
        try:
            # Check if session service is available
            if not self.session_service:
                logger.debug(
                    f"session_followup_complete_skipped | user_id={telegram_user_id} | "
                    "reason=session_service_not_available"
                )
                return

            # Get current session ID from state
            session_id = self.state_manager.get_current_session_id(telegram_user_id)
            if session_id is None:
                logger.debug(
                    f"session_followup_complete_skipped | user_id={telegram_user_id} | "
                    "reason=no_active_session"
                )
                return

            # Complete followup tracking (sets followup_finish_time and calculates duration)
            result = self.session_service.complete_followup(session_id)

            if result:
                followup_finish = (
                    result.followup_finish_time.isoformat()
                    if result.followup_finish_time
                    else "None"
                )
                logger.info(
                    f"session_followup_completed | telegram_user_id={telegram_user_id} | "
                    f"session_id={session_id} | "
                    f"followup_finish_time={followup_finish} | "
                    f"followup_duration_seconds={result.followup_duration_seconds}"
                )
            else:
                # Completing followup failed - graceful degradation, continue
                logger.warning(
                    f"session_followup_complete_failed | telegram_user_id={telegram_user_id} | "
                    f"session_id={session_id} | continuing_without_tracking"
                )

        except Exception as e:
            # Graceful degradation - session tracking failure should not block user
            logger.error(
                f"session_followup_complete_error | telegram_user_id={telegram_user_id} | "
                f"error={e}",
                exc_info=True,
            )

    async def _start_session_for_prompt(self, telegram_user_id: int, initial_prompt: str):
        """
        Start a new session when user sends their initial prompt.

        This method creates a new session record immediately when a user submits
        a prompt for optimization (before method selection). The session is created
        with optimization_method=None, which will be set later when user selects a method.

        Args:
            telegram_user_id: Telegram user ID (not database user ID)
            initial_prompt: The user's initial prompt text

        Requirements: 1.1, 1.5, 1.6
        """
        try:
            # Check if session service is available
            if not self.session_service:
                logger.debug(
                    f"session_start_skipped | user_id={telegram_user_id} | "
                    "reason=session_service_not_available"
                )
                return

            # Get the database user to obtain user_id foreign key
            if not self.user_tracking_service:
                logger.warning(
                    f"session_start_skipped | user_id={telegram_user_id} | "
                    "reason=user_tracking_service_not_available"
                )
                return

            # Get user from tracking service (user should already exist from handle_message)
            user, _ = self.user_tracking_service.get_or_create_user(telegram_user_id, None)
            if user is None:
                logger.warning(
                    f"session_start_skipped | telegram_user_id={telegram_user_id} | "
                    "reason=user_not_found"
                )
                return

            # Start the session with user_id (database ID), model_name, and method=None
            # Method will be set later when user selects optimization method
            session = self.session_service.start_session(
                user_id=user.id,
                model_name=self.config.model_name,
                method=None,  # Will be set when user selects method (Requirements 1.5)
            )

            if session:
                # Store session ID in state for later use (token tracking, completion, etc.)
                self.state_manager.set_current_session_id(telegram_user_id, session.id)
                logger.info(
                    f"session_started | telegram_user_id={telegram_user_id} | "
                    f"session_id={session.id} | method=None | "
                    f"model={self.config.model_name}"
                )

                # Track the initial user prompt immediately after session creation (Requirements 1.6)
                self._track_session_message(telegram_user_id, "user", initial_prompt)
                logger.debug(
                    f"session_initial_prompt_tracked | telegram_user_id={telegram_user_id} | "
                    f"session_id={session.id} | prompt_length={len(initial_prompt)}"
                )
            else:
                # Session creation failed - graceful degradation, continue without session
                logger.warning(
                    f"session_start_failed | telegram_user_id={telegram_user_id} | "
                    "continuing_without_session"
                )

        except Exception as e:
            # Graceful degradation - session tracking failure should not block user
            logger.error(
                f"session_start_error | telegram_user_id={telegram_user_id} | error={e}",
                exc_info=True,
            )

    def _set_session_optimization_method(self, telegram_user_id: int, method_name: str):
        """
        Set the optimization method for the current session.

        This method updates the session's optimization_method field when the user
        selects a method (LYRA, CRAFT, GGL). The session was already created in
        _start_session_for_prompt with method=None.

        Args:
            telegram_user_id: Telegram user ID (not database user ID)
            method_name: Selected optimization method name (LYRA, LYRA Basic, LYRA Detail, CRAFT, GGL)

        Requirements: 6.1
        """
        try:
            # Check if session service is available
            if not self.session_service:
                logger.debug(
                    f"session_method_update_skipped | user_id={telegram_user_id} | "
                    "reason=session_service_not_available"
                )
                return

            # Get current session ID from state
            session_id = self.state_manager.get_current_session_id(telegram_user_id)
            if session_id is None:
                logger.debug(
                    f"session_method_update_skipped | telegram_user_id={telegram_user_id} | "
                    "reason=no_current_session"
                )
                return

            # Map method name to OptimizationMethod enum
            # LYRA Basic and LYRA Detail both map to LYRA
            method_mapping = {
                "LYRA": OptimizationMethod.LYRA,
                "LYRA Basic": OptimizationMethod.LYRA,
                "LYRA Detail": OptimizationMethod.LYRA,
                "CRAFT": OptimizationMethod.CRAFT,
                "GGL": OptimizationMethod.GGL,
            }

            optimization_method = method_mapping.get(method_name)
            if optimization_method is None:
                logger.warning(
                    f"session_method_update_skipped | user_id={telegram_user_id} | "
                    f"reason=unknown_method | method={method_name}"
                )
                return

            # Update the session with the selected method
            session = self.session_service.set_optimization_method(
                session_id=session_id,
                method=optimization_method,
            )

            if session:
                logger.info(
                    f"session_method_set | telegram_user_id={telegram_user_id} | "
                    f"session_id={session_id} | method={optimization_method.value}"
                )
            else:
                # Method update failed - graceful degradation, continue without update
                logger.warning(
                    f"session_method_update_failed | telegram_user_id={telegram_user_id} | "
                    f"session_id={session_id} | method={method_name}"
                )

        except Exception as e:
            # Graceful degradation - session tracking failure should not block user
            logger.error(
                f"session_method_update_error | telegram_user_id={telegram_user_id} | "
                f"method={method_name} | error={e}",
                exc_info=True,
            )

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
            request_text = user_request or self.conversation_manager.get_user_prompt(user_id) or ""

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
                    if "parse entities" in str(e).lower() or "markdown" in str(e).lower():
                        kwargs_no_parse = {k: v for k, v in kwargs.items() if k != "parse_mode"}
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
                    kwargs_no_parse = {k: v for k, v in kwargs.items() if k != "parse_mode"}
                    await update.message.reply_text(text, **kwargs_no_parse)
                    logger.info("Message sent successfully without Markdown parsing")
                else:
                    # Re-raise for tenacity to handle
                    raise e
