"""
Email flow orchestration for email-based prompt delivery.

This module provides the main workflow coordinator that integrates
authentication, follow-up questions, and optimization for email delivery.
"""

import logging
import time
from typing import Optional

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes

from .auth_service import get_auth_service
from .config import BotConfig
from .conversation_manager import ConversationManager
from .database import mask_email, mask_telegram_id
from .email_service import get_email_service
from .graceful_degradation import (
    check_email_flow_readiness,
    get_degradation_manager,
    handle_smtp_fallback,
)
from .llm_client_base import LLMClientBase
from .messages import (
    BTN_GENERATE_PROMPT,
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
    create_prompt_input_reply,
    parse_followup_response,
)
from .redis_client import get_redis_client
from .state_manager import StateManager

logger = logging.getLogger(__name__)


class EmailFlowOrchestrator:
    """Main workflow coordinator for email-based prompt delivery."""

    def __init__(
        self,
        config: BotConfig,
        llm_client: LLMClientBase,
        conversation_manager: ConversationManager,
        state_manager: StateManager,
    ):
        """
        Initialize email flow orchestrator.

        Args:
            config: Bot configuration
            llm_client: LLM client for optimization
            conversation_manager: Conversation manager for follow-up questions
            state_manager: State manager for user states
        """
        self.config = config
        self.llm_client = llm_client
        self.conversation_manager = conversation_manager
        self.state_manager = state_manager
        self.auth_service = get_auth_service()
        self.email_service = get_email_service()
        self.redis_client = get_redis_client()

        # Timeout configuration for follow-up questions
        self.followup_timeout_seconds = config.followup_timeout_seconds

    async def start_email_authentication(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        original_prompt: str = None,
    ) -> bool:
        """
        Start the email authentication and delivery flow.
        Alias for start_email_flow for backward compatibility.
        """
        return await self.start_email_flow(update, context, user_id)

    async def start_email_flow(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int
    ) -> bool:
        """
        Start the email authentication and delivery flow.

        Args:
            update: Telegram update object
            context: Telegram context
            user_id: User's Telegram ID

        Returns:
            True if flow started successfully, False otherwise
        """
        try:
            # Get the original prompt from conversation manager
            original_prompt = self.conversation_manager.get_user_prompt(user_id)
            if not original_prompt:
                await self._safe_reply(
                    update,
                    "❌ Не удалось найти исходный промпт. Пожалуйста, начните заново.",
                    reply_markup=ReplyKeyboardMarkup(
                        [[BTN_RESET]], resize_keyboard=True
                    ),
                )
                return False

            # Check service prerequisites using graceful degradation
            can_proceed, error_message = check_email_flow_readiness("RU")
            if not can_proceed:
                await self._safe_reply(
                    update,
                    error_message or ERROR_REDIS_UNAVAILABLE,
                    reply_markup=ReplyKeyboardMarkup(
                        [[BTN_RESET]], resize_keyboard=True
                    ),
                )
                logger.warning(
                    f"email_flow_blocked_prerequisites_failed | user_id={mask_telegram_id(user_id)} | reason={error_message}"
                )
                return False

            # Check if user is already authenticated
            if self.auth_service.is_user_authenticated(user_id):
                # User is already authenticated, skip OTP and proceed directly
                user_email = self.auth_service.get_user_email(user_id)
                await self._safe_reply(
                    update,
                    EMAIL_ALREADY_AUTHENTICATED.format(email=mask_email(user_email)),
                    reply_markup=ReplyKeyboardMarkup(
                        [[BTN_RESET]], resize_keyboard=True
                    ),
                )

                # Store email flow data with existing email
                self.state_manager.set_email_flow_data(
                    user_id,
                    {
                        "original_prompt": original_prompt,
                        "email": user_email,
                        "authenticated": True,
                    },
                )

                logger.info(
                    f"email_flow_authenticated_user | user_id={mask_telegram_id(user_id)} | email={mask_email(user_email)}"
                )

                # Proceed directly to follow-up questions and email delivery
                return await self._proceed_to_followup_and_delivery(
                    update, context, user_id
                )

            # User not authenticated, start normal email input flow
            # Store email flow data
            self.state_manager.set_email_flow_data(
                user_id, {"original_prompt": original_prompt}
            )

            # Set state to waiting for email input
            self.state_manager.set_waiting_for_prompt(user_id, False)
            self.state_manager.set_waiting_for_email_input(user_id, True)

            # Ask for email address
            await self._safe_reply(
                update,
                EMAIL_INPUT_MESSAGE,
                reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True),
            )

            logger.info(f"email_flow_started | user_id={mask_telegram_id(user_id)}")
            return True

        except Exception as e:
            logger.error(
                f"Error starting email flow for user {mask_telegram_id(user_id)}: {e}",
                exc_info=True,
            )
            await self._safe_reply(
                update,
                "❌ Произошла ошибка при запуске email-потока. Попробуйте позже.",
                reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True),
            )
            return False

    async def handle_email_input(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        text: str,
    ) -> bool:
        """
        Handle email address input and validation.

        Args:
            update: Telegram update object
            context: Telegram context
            user_id: User's Telegram ID
            text: Email address input

        Returns:
            True if handled successfully, False otherwise
        """
        try:
            # Validate email format
            if not self.auth_service.validate_email_format(text):
                await self._safe_reply(
                    update,
                    ERROR_EMAIL_INVALID,
                    reply_markup=ReplyKeyboardMarkup(
                        [[BTN_RESET]], resize_keyboard=True
                    ),
                )
                return False

            # Send OTP via authentication service
            success, message, otp = self.auth_service.send_otp(
                user_id, text.strip(), text
            )

            if not success:
                # Handle different error types
                if "rate_limited" in message:
                    await self._safe_reply(
                        update,
                        ERROR_EMAIL_RATE_LIMITED,
                        reply_markup=ReplyKeyboardMarkup(
                            [[BTN_RESET]], resize_keyboard=True
                        ),
                    )
                else:
                    await self._safe_reply(
                        update,
                        ERROR_EMAIL_SEND_FAILED,
                        reply_markup=ReplyKeyboardMarkup(
                            [[BTN_RESET]], resize_keyboard=True
                        ),
                    )
                logger.warning(
                    f"email_input_failed | user_id={mask_telegram_id(user_id)} | reason={message}"
                )
                return False

            # Send OTP via email service
            email_result = await self.email_service.send_otp_email(
                text.strip(), otp, user_id
            )
            if not email_result.success:
                logger.error(
                    f"Failed to send OTP email to {mask_email(text)} for user {mask_telegram_id(user_id)}: {email_result.error}"
                )
                await self._safe_reply(
                    update,
                    ERROR_EMAIL_SEND_FAILED,
                    reply_markup=ReplyKeyboardMarkup(
                        [[BTN_RESET]], resize_keyboard=True
                    ),
                )
                return False

            # Update email flow data
            email_flow_data = self.state_manager.get_email_flow_data(user_id) or {}
            email_flow_data.update(
                {"email": text.strip().lower(), "email_original": text}
            )
            self.state_manager.set_email_flow_data(user_id, email_flow_data)

            # Move to OTP input state
            self.state_manager.set_waiting_for_email_input(user_id, False)
            self.state_manager.set_waiting_for_otp_input(user_id, True)

            await self._safe_reply(
                update,
                EMAIL_OTP_SENT.format(email=mask_email(text.strip())),
                reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True),
            )

            logger.info(
                f"email_input_processed | user_id={mask_telegram_id(user_id)} | email={mask_email(text.strip())}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Error handling email input for user {mask_telegram_id(user_id)}: {e}",
                exc_info=True,
            )
            await self._safe_reply(
                update,
                "❌ Произошла ошибка при обработке email. Попробуйте позже.",
                reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True),
            )
            return False

    async def handle_otp_verification(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        otp: str,
    ) -> bool:
        """
        Handle OTP verification.
        Alias for handle_otp_input for backward compatibility.
        """
        return await self.handle_otp_input(update, context, user_id, otp)

    async def handle_otp_input(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        text: str,
    ) -> bool:
        """
        Handle OTP code input and verification.

        Args:
            update: Telegram update object
            context: Telegram context
            user_id: User's Telegram ID
            text: OTP code input

        Returns:
            True if handled successfully, False otherwise
        """
        try:
            # Validate OTP format (6 digits)
            if not (text.strip().isdigit() and len(text.strip()) == 6):
                await self._safe_reply(
                    update,
                    "❌ Код должен состоять из 6 цифр. Попробуйте еще раз:",
                    reply_markup=ReplyKeyboardMarkup(
                        [[BTN_RESET]], resize_keyboard=True
                    ),
                )
                return False

            # Verify OTP with authentication service
            success, error_reason = self.auth_service.verify_otp(user_id, text.strip())

            if success:
                # Successful verification
                self.state_manager.set_waiting_for_otp_input(user_id, False)

                await self._safe_reply(
                    update,
                    OTP_VERIFICATION_SUCCESS,
                    reply_markup=ReplyKeyboardMarkup(
                        [[BTN_RESET]], resize_keyboard=True
                    ),
                )

                logger.info(f"otp_verified | user_id={mask_telegram_id(user_id)}")

                # Proceed to follow-up questions and email delivery
                return await self._proceed_to_followup_and_delivery(
                    update, context, user_id
                )

            else:
                # Handle verification failure
                if "expired" in error_reason:
                    await self._safe_reply(
                        update,
                        ERROR_OTP_EXPIRED,
                        reply_markup=ReplyKeyboardMarkup(
                            [[BTN_RESET]], resize_keyboard=True
                        ),
                    )
                    self._reset_user_state(user_id)
                    return False
                elif "attempt_limit" in error_reason:
                    await self._safe_reply(
                        update,
                        ERROR_OTP_ATTEMPTS_EXCEEDED,
                        reply_markup=ReplyKeyboardMarkup(
                            [[BTN_RESET]], resize_keyboard=True
                        ),
                    )
                    self._reset_user_state(user_id)
                    return False
                else:
                    # Invalid OTP, allow retry
                    await self._safe_reply(
                        update,
                        ERROR_OTP_INVALID,
                        reply_markup=ReplyKeyboardMarkup(
                            [[BTN_RESET]], resize_keyboard=True
                        ),
                    )
                    return False

        except Exception as e:
            logger.error(
                f"Error handling OTP input for user {mask_telegram_id(user_id)}: {e}",
                exc_info=True,
            )
            await self._safe_reply(
                update,
                "❌ Произошла ошибка при проверке кода. Попробуйте позже.",
                reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True),
            )
            return False

    async def _proceed_to_followup_and_delivery(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int
    ) -> bool:
        """
        Proceed to follow-up questions and email delivery for authenticated users.

        Args:
            update: Telegram update object
            context: Telegram context
            user_id: User's Telegram ID

        Returns:
            True if proceeded successfully, False otherwise
        """
        try:
            # Check service health using graceful degradation
            try:
                degradation_manager = get_degradation_manager()
                from .graceful_degradation import ServiceType

                smtp_available = degradation_manager.is_service_available(
                    ServiceType.SMTP
                )

                if not smtp_available:
                    # SMTP unhealthy, get appropriate user message
                    user_message = degradation_manager.get_user_message("RU")
                    await self._safe_reply(
                        update,
                        user_message,
                        reply_markup=ReplyKeyboardMarkup(
                            [[BTN_RESET]], resize_keyboard=True
                        ),
                    )
                    logger.warning(
                        f"email_delivery_fallback_smtp_unhealthy | user_id={mask_telegram_id(user_id)} | smtp_available={smtp_available}"
                    )

                    # Implement chat-only delivery of 3 optimized prompts
                    return await self._deliver_prompts_to_chat(update, context, user_id)

            except RuntimeError:
                # Degradation manager not initialized, fall back to direct health check
                if not self.email_service.health_check():
                    await self._safe_reply(
                        update,
                        ERROR_SMTP_UNAVAILABLE,
                        reply_markup=ReplyKeyboardMarkup(
                            [[BTN_RESET]], resize_keyboard=True
                        ),
                    )
                    logger.warning(
                        f"email_delivery_fallback_smtp_unhealthy_direct | user_id={mask_telegram_id(user_id)}"
                    )
                    return await self._deliver_prompts_to_chat(update, context, user_id)

            # Start follow-up questions integration
            return await self._start_followup_questions(update, context, user_id)

        except Exception as e:
            logger.error(
                f"Error proceeding to follow-up and delivery for user {mask_telegram_id(user_id)}: {e}",
                exc_info=True,
            )
            await self._safe_reply(
                update,
                "❌ Произошла ошибка при переходе к улучшению промпта. Попробуйте позже.",
                reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True),
            )
            return False

    async def start_followup_questions(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        improved_prompt: str = None,
    ) -> bool:
        """
        Start follow-up questions for the user.
        Public interface for starting follow-up questions.
        """
        return await self._start_followup_questions(update, context, user_id)

    async def _start_followup_questions(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int
    ) -> bool:
        """
        Start follow-up questions integration with existing system.

        Args:
            update: Telegram update object
            context: Telegram context
            user_id: User's Telegram ID

        Returns:
            True if started successfully, False otherwise
        """
        try:
            # Get original prompt from email flow data
            email_flow_data = self.state_manager.get_email_flow_data(user_id)
            if not email_flow_data:
                logger.error(
                    f"No email flow data found for user {mask_telegram_id(user_id)}"
                )
                return False

            original_prompt = email_flow_data.get("original_prompt")
            if not original_prompt:
                logger.error(
                    f"No original prompt found in email flow data for user {mask_telegram_id(user_id)}"
                )
                return False

            # First, run initial optimization to get improved prompt
            improved_prompt = await self._get_improved_prompt(original_prompt, user_id)
            if not improved_prompt:
                logger.error(
                    f"Failed to get improved prompt for user {mask_telegram_id(user_id)}"
                )
                # Fallback to original prompt
                improved_prompt = original_prompt

            # Cache the improved prompt for follow-up conversation context
            self.state_manager.set_improved_prompt_cache(user_id, improved_prompt)

            # Offer follow-up questions to user
            await self._safe_reply(
                update,
                FOLLOWUP_OFFER_MESSAGE,
                parse_mode="Markdown",
                reply_markup=FOLLOWUP_CHOICE_KEYBOARD,
            )

            # Set state to waiting for follow-up choice
            self.state_manager.set_waiting_for_followup_choice(user_id, True)

            logger.info(
                f"followup_questions_offered | user_id={mask_telegram_id(user_id)}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Error starting follow-up questions for user {mask_telegram_id(user_id)}: {e}",
                exc_info=True,
            )
            return False

    async def handle_followup_choice(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        text: str,
    ) -> bool:
        """
        Handle follow-up choice (YES/NO) from user.

        Args:
            update: Telegram update object
            context: Telegram context
            user_id: User's Telegram ID
            text: User's choice (YES/NO)

        Returns:
            True if handled successfully, False otherwise
        """
        try:
            if text == BTN_NO:
                # User declined follow-up questions - proceed directly to optimization and email delivery
                logger.info(f"followup_declined | user_id={mask_telegram_id(user_id)}")

                # Get cached improved prompt
                improved_prompt = self.state_manager.get_improved_prompt_cache(user_id)
                if not improved_prompt:
                    # Fallback if cache is missing
                    email_flow_data = self.state_manager.get_email_flow_data(user_id)
                    improved_prompt = email_flow_data.get("original_prompt", "")

                # Reset follow-up state
                self.state_manager.set_waiting_for_followup_choice(user_id, False)

                # Proceed directly to optimization and email delivery
                return await self._run_optimization_and_email_delivery(
                    update, context, user_id, improved_prompt
                )

            elif text == BTN_YES:
                # User accepted follow-up questions
                # Get cached improved prompt
                improved_prompt = self.state_manager.get_improved_prompt_cache(user_id)
                if not improved_prompt:
                    # Fallback if cache is missing - should not happen in normal flow
                    logger.warning(
                        f"followup_accepted_no_cache | user_id={mask_telegram_id(user_id)}"
                    )
                    email_flow_data = self.state_manager.get_email_flow_data(user_id)
                    improved_prompt = email_flow_data.get("original_prompt", "")

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

                # Update state to wait for prompt input
                self.state_manager.set_waiting_for_followup_choice(user_id, False)
                self.state_manager.set_waiting_for_followup_prompt_input(user_id, True)

                logger.info(
                    f"followup_accepted_prompt_input | user_id={mask_telegram_id(user_id)}"
                )
                return True

            else:
                # Invalid choice, ignore
                logger.warning(
                    f"invalid_followup_choice | user_id={mask_telegram_id(user_id)} | text={text}"
                )
                return False

        except Exception as e:
            logger.error(
                f"Error handling follow-up choice for user {mask_telegram_id(user_id)}: {e}",
                exc_info=True,
            )
            return False

    async def handle_followup_prompt_input(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        text: str,
    ) -> bool:
        """
        Handle user prompt input from ForceReply during follow-up flow.

        Args:
            update: Telegram update object
            context: Telegram context
            user_id: User's Telegram ID
            text: User's prompt input

        Returns:
            True if handled successfully, False otherwise
        """
        try:
            logger.info(
                f"followup_prompt_input | user_id={mask_telegram_id(user_id)} | length={len(text)}"
            )

            # Start follow-up conversation with the received prompt
            self.conversation_manager.start_followup_conversation(user_id, text)

            # Reset token counters to start new accumulation session for follow-up only
            self.conversation_manager.reset_token_totals(user_id)

            # Update state transitions
            self.state_manager.set_waiting_for_followup_prompt_input(user_id, False)
            self.state_manager.set_in_followup_conversation(user_id, True)

            # Store timeout start time for graceful degradation
            self._set_followup_timeout(user_id)

            logger.info(
                f"followup_conversation_started | user_id={mask_telegram_id(user_id)}"
            )

            # Send initial request to LLM to start asking questions
            return await self._process_followup_llm_request(update, context, user_id)

        except Exception as e:
            logger.error(
                f"Error handling follow-up prompt input for user {mask_telegram_id(user_id)}: {e}",
                exc_info=True,
            )
            return False

    async def handle_followup_conversation(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        text: str,
    ) -> bool:
        """
        Handle follow-up conversation during question-answer phase.

        Args:
            update: Telegram update object
            context: Telegram context
            user_id: User's Telegram ID
            text: User's response

        Returns:
            True if handled successfully, False otherwise
        """
        try:
            # Check for timeout before processing
            if self._is_followup_timeout(user_id):
                logger.info(
                    f"followup_timeout_detected | user_id={mask_telegram_id(user_id)}"
                )
                return await self._handle_followup_timeout(update, context, user_id)

            # Check if user clicked the generate prompt button
            if text == BTN_GENERATE_PROMPT:
                return await self._process_followup_generation(update, context, user_id)

            # Add user response to conversation history
            self.conversation_manager.append_message(user_id, "user", text)

            logger.info(
                f"followup_user_response | user_id={mask_telegram_id(user_id)} | length={len(text)}"
            )

            # Send user response to LLM and get next question or refined prompt
            return await self._process_followup_llm_request(update, context, user_id)

        except Exception as e:
            logger.error(
                f"Error handling follow-up conversation for user {mask_telegram_id(user_id)}: {e}",
                exc_info=True,
            )
            return await self._handle_followup_error(update, context, user_id, e)

    async def _get_improved_prompt(self, original_prompt: str, user_id: int) -> str:
        """
        Get improved prompt using initial optimization.

        Args:
            original_prompt: Original user prompt
            user_id: User's Telegram ID

        Returns:
            Improved prompt or original if optimization fails
        """
        try:
            # Use CRAFT method for initial improvement
            system_prompt = self.conversation_manager.prompt_loader.craft_prompt
            transcript = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": original_prompt},
            ]

            response = await self.llm_client.send_prompt(transcript)
            if response and response.strip():
                logger.info(
                    f"improved_prompt_generated | user_id={mask_telegram_id(user_id)}"
                )
                return response.strip()
            else:
                logger.warning(
                    f"empty_improved_prompt | user_id={mask_telegram_id(user_id)}"
                )
                return original_prompt

        except Exception as e:
            logger.error(
                f"Error getting improved prompt for user {mask_telegram_id(user_id)}: {e}"
            )
            return original_prompt

    def _set_followup_timeout(self, user_id: int) -> None:
        """Set follow-up timeout start time."""
        timeout_data = {"start_time": time.time()}
        self.redis_client.set_flow_state(
            user_id, "followup_timeout", timeout_data, ttl=self.followup_timeout_seconds
        )

    def _is_followup_timeout(self, user_id: int) -> bool:
        """Check if follow-up conversation has timed out."""
        try:
            timeout_data = self.redis_client.get_flow_state(user_id)
            if not timeout_data or timeout_data.get("state") != "followup_timeout":
                return False

            start_time = timeout_data.get("start_time", 0)
            elapsed = time.time() - start_time
            return elapsed > self.followup_timeout_seconds

        except Exception as e:
            logger.error(f"Error checking follow-up timeout: {e}")
            return False

    async def _handle_followup_timeout(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int
    ) -> bool:
        """
        Handle follow-up timeout with graceful degradation.

        Args:
            update: Telegram update object
            context: Telegram context
            user_id: User's Telegram ID

        Returns:
            True if handled successfully, False otherwise
        """
        try:
            logger.info(
                f"followup_timeout_fallback | user_id={mask_telegram_id(user_id)}"
            )

            # Try to fallback to cached improved prompt
            improved_prompt = self.state_manager.get_improved_prompt_cache(user_id)
            if not improved_prompt:
                # Fallback to original prompt from email flow data
                email_flow_data = self.state_manager.get_email_flow_data(user_id)
                improved_prompt = email_flow_data.get("original_prompt", "")

            # Clear follow-up state
            self.state_manager.set_in_followup_conversation(user_id, False)
            self.redis_client.delete_flow_state(user_id)

            # Proceed with best-effort improved prompt
            return await self._run_optimization_and_email_delivery(
                update, context, user_id, improved_prompt
            )

        except Exception as e:
            logger.error(
                f"Error handling follow-up timeout for user {mask_telegram_id(user_id)}: {e}",
                exc_info=True,
            )
            return False

    async def _handle_followup_error(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        error: Exception,
    ) -> bool:
        """
        Handle errors during follow-up conversations with graceful degradation.

        Args:
            update: Telegram update object
            context: Telegram context
            user_id: User's Telegram ID
            error: The exception that occurred

        Returns:
            True if handled successfully, False otherwise
        """
        try:
            logger.error(
                f"followup_error_fallback | user_id={mask_telegram_id(user_id)} | error={str(error)}"
            )

            # Try to fallback to cached improved prompt
            improved_prompt = self.state_manager.get_improved_prompt_cache(user_id)
            if not improved_prompt:
                # Fallback to original prompt from email flow data
                email_flow_data = self.state_manager.get_email_flow_data(user_id)
                improved_prompt = email_flow_data.get("original_prompt", "")

            # Clear follow-up state
            self.state_manager.set_in_followup_conversation(user_id, False)
            self.redis_client.delete_flow_state(user_id)

            # Proceed with best-effort improved prompt
            return await self._run_optimization_and_email_delivery(
                update, context, user_id, improved_prompt
            )

        except Exception as e:
            logger.error(
                f"Error handling follow-up error for user {mask_telegram_id(user_id)}: {e}",
                exc_info=True,
            )
            return False

    async def _process_followup_llm_request(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int
    ) -> bool:
        """
        Process LLM request during follow-up conversation.

        Args:
            update: Telegram update object
            context: Telegram context
            user_id: User's Telegram ID

        Returns:
            True if processed successfully, False otherwise
        """
        try:
            # Check for timeout before processing
            if self._is_followup_timeout(user_id):
                return await self._handle_followup_timeout(update, context, user_id)

            transcript = self.conversation_manager.get_transcript(user_id)
            if not transcript:
                logger.error(
                    f"No transcript found for follow-up conversation | user_id={mask_telegram_id(user_id)}"
                )
                return False

            # Send request to LLM
            raw_response = await self.llm_client.send_prompt(transcript)

            # Track token usage
            usage = self.llm_client.get_last_usage()
            self.conversation_manager.accumulate_token_usage(user_id, usage)

            # Add LLM response to conversation history
            self.conversation_manager.append_message(user_id, "assistant", raw_response)

            # Parse response
            parsed_response, is_refined_prompt = parse_followup_response(raw_response)

            if is_refined_prompt:
                # LLM provided refined prompt, complete the follow-up flow
                return await self._complete_followup_conversation(
                    update, context, user_id, parsed_response
                )
            else:
                # LLM asked another question, continue conversation
                await self._safe_reply(
                    update,
                    parsed_response,
                    parse_mode="Markdown",
                    reply_markup=FOLLOWUP_CONVERSATION_KEYBOARD,
                )
                logger.info(
                    f"followup_question_sent | user_id={mask_telegram_id(user_id)}"
                )
                return True

        except Exception as e:
            logger.error(
                f"Error processing follow-up LLM request for user {mask_telegram_id(user_id)}: {e}",
                exc_info=True,
            )
            return await self._handle_followup_error(update, context, user_id, e)

    async def _process_followup_generation(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int
    ) -> bool:
        """
        Handle generate prompt button click during follow-up conversation.

        Args:
            update: Telegram update object
            context: Telegram context
            user_id: User's Telegram ID

        Returns:
            True if processed successfully, False otherwise
        """
        try:
            # Send the generate signal to LLM
            self.conversation_manager.append_message(
                user_id, "user", "<GENERATE_PROMPT>"
            )

            logger.info(
                f"followup_generate_requested | user_id={mask_telegram_id(user_id)}"
            )

            return await self._process_followup_llm_request(update, context, user_id)

        except Exception as e:
            logger.error(
                f"Error processing follow-up generation for user {mask_telegram_id(user_id)}: {e}",
                exc_info=True,
            )
            return await self._handle_followup_error(update, context, user_id, e)

    async def _complete_followup_conversation(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        refined_prompt: str,
    ) -> bool:
        """
        Complete the follow-up conversation and proceed to optimization and email delivery.

        Args:
            update: Telegram update object
            context: Telegram context
            user_id: User's Telegram ID
            refined_prompt: Final refined prompt from follow-up conversation

        Returns:
            True if completed successfully, False otherwise
        """
        try:
            # Clear follow-up state
            self.state_manager.set_in_followup_conversation(user_id, False)
            self.redis_client.delete_flow_state(user_id)

            logger.info(f"followup_completed | user_id={mask_telegram_id(user_id)}")

            # Proceed to optimization and email delivery with refined prompt
            return await self._run_optimization_and_email_delivery(
                update, context, user_id, refined_prompt
            )

        except Exception as e:
            logger.error(
                f"Error completing follow-up conversation for user {mask_telegram_id(user_id)}: {e}",
                exc_info=True,
            )
            return False

    async def _run_optimization_and_email_delivery(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        improved_prompt: str,
    ) -> bool:
        """
        Run all three optimization methods and deliver results via email.

        Args:
            update: Telegram update object
            context: Telegram context
            user_id: User's Telegram ID
            improved_prompt: Improved prompt to optimize

        Returns:
            True if completed successfully, False otherwise
        """
        try:
            logger.info(
                f"optimization_and_delivery_started | user_id={mask_telegram_id(user_id)}"
            )

            # Show processing message to user
            await self._safe_reply(
                update,
                "🔄 Запускаем оптимизацию промпта всеми тремя методами...",
                reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True),
            )

            # Run all three optimization methods
            optimization_results = await self._run_all_optimizations(
                improved_prompt, user_id
            )

            if not optimization_results:
                logger.error(
                    f"Failed to get optimization results for user {mask_telegram_id(user_id)}"
                )
                await self._safe_reply(
                    update,
                    "❌ Не удалось выполнить оптимизацию промпта. Попробуйте позже.",
                    reply_markup=ReplyKeyboardMarkup(
                        [[BTN_RESET]], resize_keyboard=True
                    ),
                )
                self._reset_user_state(user_id)
                return False

            # Get email flow data for original prompt and email
            email_flow_data = self.state_manager.get_email_flow_data(user_id)
            if not email_flow_data:
                logger.error(
                    f"No email flow data found for user {mask_telegram_id(user_id)}"
                )
                self._reset_user_state(user_id)
                return False

            original_prompt = email_flow_data.get("original_prompt", "")
            user_email = email_flow_data.get("email", "")

            # Send comprehensive email with all results
            email_success = await self._send_optimization_email(
                user_email,
                original_prompt,
                improved_prompt,
                optimization_results,
                user_id,
            )

            if email_success:
                # Email sent successfully
                await self._safe_reply(
                    update,
                    f"✅ Оптимизированные промпты отправлены на {mask_email(user_email)}!",
                    reply_markup=ReplyKeyboardMarkup(
                        [[BTN_RESET]], resize_keyboard=True
                    ),
                )
                logger.info(
                    f"optimization_email_sent | user_id={mask_telegram_id(user_id)} | email={mask_email(user_email)}"
                )
            else:
                # Email failed, fallback to chat delivery
                await self._safe_reply(
                    update,
                    "📧 Отправка email временно недоступна. Результаты будут показаны в чате.",
                )

                # Send the optimized prompts to chat
                await self._send_fallback_prompts_to_chat(update, optimization_results)

                logger.info(
                    f"optimization_fallback_chat | user_id={mask_telegram_id(user_id)}"
                )

            # Reset states since we're done with email flow
            self._reset_user_state(user_id)
            return True

        except Exception as e:
            logger.error(
                f"Error running optimization and email delivery for user {mask_telegram_id(user_id)}: {e}",
                exc_info=True,
            )
            await self._safe_reply(
                update,
                "❌ Произошла ошибка при оптимизации и отправке. Попробуйте позже.",
                reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True),
            )
            self._reset_user_state(user_id)
            return False

    async def _run_all_optimizations(
        self, improved_prompt: str, user_id: int
    ) -> Optional[dict]:
        """
        Run all three optimization methods (CRAFT, LYRA, GGL) on the improved prompt.

        Args:
            improved_prompt: The improved prompt to optimize
            user_id: User's Telegram ID for logging

        Returns:
            Dictionary with optimization results or None if failed
        """
        try:
            # Get system prompts for all three methods
            craft_system_prompt = self.conversation_manager.prompt_loader.craft_prompt
            lyra_system_prompt = self.conversation_manager.prompt_loader.lyra_prompt
            ggl_system_prompt = self.conversation_manager.prompt_loader.ggl_prompt

            # Prepare transcripts for all three methods
            craft_transcript = [
                {"role": "system", "content": craft_system_prompt},
                {"role": "user", "content": improved_prompt},
            ]

            lyra_transcript = [
                {"role": "system", "content": lyra_system_prompt},
                {"role": "user", "content": improved_prompt},
            ]

            ggl_transcript = [
                {"role": "system", "content": ggl_system_prompt},
                {"role": "user", "content": improved_prompt},
            ]

            logger.info(
                f"optimization_methods_starting | user_id={mask_telegram_id(user_id)}"
            )

            # Run all three optimizations using individual methods
            craft_result = await self._run_craft_optimization(improved_prompt)
            lyra_result = await self._run_lyra_optimization(improved_prompt)
            ggl_result = await self._run_ggl_optimization(improved_prompt)

            # Check if all optimizations succeeded
            if not craft_result or not lyra_result or not ggl_result:
                logger.error(
                    f"One or more optimizations failed for user {mask_telegram_id(user_id)}"
                )
                return None

            results = {
                "craft": craft_result,
                "lyra": lyra_result,
                "ggl": ggl_result,
            }

            logger.info(
                f"optimization_methods_completed | user_id={mask_telegram_id(user_id)}"
            )
            return results

        except Exception as e:
            logger.error(
                f"Error running optimizations for user {mask_telegram_id(user_id)}: {e}",
                exc_info=True,
            )
            return None

    async def _run_single_optimization(
        self, method_name: str, transcript: list, user_id: int
    ) -> Optional[str]:
        """
        Run a single optimization method.

        Args:
            method_name: Name of the optimization method (CRAFT, LYRA, GGL)
            transcript: LLM transcript for the method
            user_id: User's Telegram ID for logging

        Returns:
            Optimization result or None if failed
        """
        try:
            logger.info(
                f"optimization_method_start | user_id={mask_telegram_id(user_id)} | method={method_name}"
            )

            response = await self.llm_client.send_prompt(transcript)

            if response and response.strip():
                logger.info(
                    f"optimization_method_success | user_id={mask_telegram_id(user_id)} | method={method_name}"
                )
                return response.strip()
            else:
                logger.warning(
                    f"optimization_method_empty | user_id={mask_telegram_id(user_id)} | method={method_name}"
                )
                return None

        except Exception as e:
            logger.error(
                f"optimization_method_error | user_id={mask_telegram_id(user_id)} | method={method_name} | error={str(e)}"
            )
            return None

    async def _send_optimization_email(
        self,
        user_email: str,
        original_prompt: str,
        improved_prompt: str,
        optimization_results: dict,
        user_id: int,
    ) -> bool:
        """
        Send comprehensive email with all optimization results.

        Args:
            user_email: User's email address
            original_prompt: Original user prompt
            improved_prompt: Improved prompt from follow-up
            optimization_results: Dictionary with CRAFT, LYRA, GGL results
            user_id: User's Telegram ID for logging

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            logger.info(
                f"optimization_email_compose | user_id={mask_telegram_id(user_id)} | email={mask_email(user_email)}"
            )

            # Send optimization results email
            email_result = await self.email_service.send_optimized_prompts_email(
                user_email,
                original_prompt,
                improved_prompt,
                optimization_results["craft"],
                optimization_results["lyra"],
                optimization_results["ggl"],
                user_id,
            )

            if email_result.success:
                logger.info(
                    f"optimization_email_success | user_id={mask_telegram_id(user_id)} | email={mask_email(user_email)}"
                )
                return True
            else:
                logger.error(
                    f"optimization_email_failed | user_id={mask_telegram_id(user_id)} | email={mask_email(user_email)} | error={email_result.error}"
                )
                return False

        except Exception as e:
            logger.error(
                f"Error sending optimization email for user {mask_telegram_id(user_id)}: {e}",
                exc_info=True,
            )
            return False

    async def _run_craft_optimization(self, prompt: str) -> str:
        """
        Run CRAFT optimization method.

        Args:
            prompt: Prompt to optimize

        Returns:
            Optimized prompt using CRAFT method
        """
        try:
            craft_system_prompt = self.conversation_manager.prompt_loader.craft_prompt
            transcript = [
                {"role": "system", "content": craft_system_prompt},
                {"role": "user", "content": prompt},
            ]

            response = await self.llm_client.send_prompt(transcript)
            return response.strip() if response else ""
        except Exception as e:
            logger.error(f"Error in CRAFT optimization: {e}")
            return ""

    async def _run_lyra_optimization(self, prompt: str) -> str:
        """
        Run LYRA optimization method.

        Args:
            prompt: Prompt to optimize

        Returns:
            Optimized prompt using LYRA method
        """
        try:
            lyra_system_prompt = self.conversation_manager.prompt_loader.lyra_prompt
            transcript = [
                {"role": "system", "content": lyra_system_prompt},
                {"role": "user", "content": prompt},
            ]

            response = await self.llm_client.send_prompt(transcript)
            return response.strip() if response else ""
        except Exception as e:
            logger.error(f"Error in LYRA optimization: {e}")
            return ""

    async def _run_ggl_optimization(self, prompt: str) -> str:
        """
        Run GGL optimization method.

        Args:
            prompt: Prompt to optimize

        Returns:
            Optimized prompt using GGL method
        """
        try:
            ggl_system_prompt = self.conversation_manager.prompt_loader.ggl_prompt
            transcript = [
                {"role": "system", "content": ggl_system_prompt},
                {"role": "user", "content": prompt},
            ]

            response = await self.llm_client.send_prompt(transcript)
            return response.strip() if response else ""
        except Exception as e:
            logger.error(f"Error in GGL optimization: {e}")
            return ""

    async def _send_fallback_prompts_to_chat(
        self, update: Update, optimization_results: dict
    ) -> None:
        """
        Send only the 3 optimized prompts to chat as fallback (strict fallback).

        Args:
            update: Telegram update object
            optimization_results: Dictionary with CRAFT, LYRA, GGL results
        """
        try:
            # Send each optimized prompt as a separate message
            methods = [
                ("CRAFT", optimization_results.get("craft", "")),
                ("LYRA", optimization_results.get("lyra", "")),
                ("GGL", optimization_results.get("ggl", "")),
            ]

            for method_name, prompt in methods:
                if prompt:
                    message = (
                        f"🔹 **{method_name} оптимизированный промпт:**\n\n{prompt}"
                    )
                    await self._safe_reply(
                        update,
                        message,
                        parse_mode="Markdown",
                    )

            # Send final message with reset button
            await self._safe_reply(
                update,
                "✅ Все оптимизированные промпты отправлены в чат!",
                reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True),
            )

        except Exception as e:
            logger.error(f"Error sending fallback prompts to chat: {e}", exc_info=True)

    async def _deliver_prompts_to_chat(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int
    ) -> bool:
        """
        Deliver 3 optimized prompts to chat when email is unavailable.

        Args:
            update: Telegram update object
            context: Telegram context
            user_id: User's Telegram ID

        Returns:
            True if delivered successfully, False otherwise
        """
        try:
            # Get email flow data
            email_flow_data = self.state_manager.get_email_flow_data(user_id)
            if not email_flow_data:
                logger.error(
                    f"No email flow data found for user {mask_telegram_id(user_id)}"
                )
                return False

            original_prompt = email_flow_data.get("original_prompt", "")
            if not original_prompt:
                logger.error(
                    f"No original prompt found for user {mask_telegram_id(user_id)}"
                )
                return False

            # Get improved prompt (use original as fallback)
            improved_prompt = await self._get_improved_prompt(original_prompt, user_id)
            if not improved_prompt:
                improved_prompt = original_prompt

            # Run all three optimization methods
            optimization_results = await self._run_all_optimizations(
                improved_prompt, user_id
            )

            if not optimization_results:
                logger.error(
                    f"Failed to get optimization results for chat delivery for user {mask_telegram_id(user_id)}"
                )
                await self._safe_reply(
                    update,
                    "❌ Не удалось выполнить оптимизацию промпта. Попробуйте позже.",
                    reply_markup=ReplyKeyboardMarkup(
                        [[BTN_RESET]], resize_keyboard=True
                    ),
                )
                self._reset_user_state(user_id)
                return False

            # Send only the 3 optimized prompts to chat (strict fallback)
            await self._send_fallback_prompts_to_chat(update, optimization_results)

            logger.info(
                f"chat_delivery_completed | user_id={mask_telegram_id(user_id)}"
            )

            # Reset states since we're done
            self._reset_user_state(user_id)
            return True

        except Exception as e:
            logger.error(
                f"Error delivering prompts to chat for user {mask_telegram_id(user_id)}: {e}",
                exc_info=True,
            )
            self._reset_user_state(user_id)
            return False

    def _reset_user_state(self, user_id: int) -> None:
        """Reset user state after email flow completion."""
        self.state_manager.set_waiting_for_prompt(user_id, True)
        self.state_manager.set_waiting_for_email_input(user_id, False)
        self.state_manager.set_waiting_for_otp_input(user_id, False)
        self.state_manager.set_waiting_for_followup_choice(user_id, False)
        self.state_manager.set_waiting_for_followup_prompt_input(user_id, False)
        self.state_manager.set_in_followup_conversation(user_id, False)
        self.state_manager.set_improved_prompt_cache(user_id, None)
        self.state_manager.set_email_flow_data(user_id, None)
        self.conversation_manager.reset(user_id)
        self.redis_client.delete_flow_state(user_id)

    async def _safe_reply(
        self, update: Update, text: str, parse_mode: str = None, reply_markup=None
    ) -> None:
        """Safely send reply to user with error handling."""
        try:
            await update.message.reply_text(
                text, parse_mode=parse_mode, reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error sending reply: {e}")
            # Try without parse_mode as fallback
            try:
                await update.message.reply_text(text, reply_markup=reply_markup)
            except Exception as e2:
                logger.error(f"Error sending fallback reply: {e2}")


# Global email flow orchestrator instance
email_flow_orchestrator: Optional[EmailFlowOrchestrator] = None


def init_email_flow_orchestrator(
    config: BotConfig,
    llm_client: LLMClientBase,
    conversation_manager: ConversationManager,
    state_manager: StateManager,
) -> EmailFlowOrchestrator:
    """
    Initialize global email flow orchestrator.

    Args:
        config: Bot configuration
        llm_client: LLM client for optimization
        conversation_manager: Conversation manager for follow-up questions
        state_manager: State manager for user states

    Returns:
        EmailFlowOrchestrator instance
    """
    global email_flow_orchestrator
    email_flow_orchestrator = EmailFlowOrchestrator(
        config, llm_client, conversation_manager, state_manager
    )
    return email_flow_orchestrator


def get_email_flow_orchestrator() -> EmailFlowOrchestrator:
    """
    Get the global email flow orchestrator instance.

    Returns:
        EmailFlowOrchestrator instance

    Raises:
        RuntimeError: If email flow orchestrator is not initialized
    """
    if email_flow_orchestrator is None:
        raise RuntimeError(
            "Email flow orchestrator not initialized. Call init_email_flow_orchestrator() first."
        )
    return email_flow_orchestrator
