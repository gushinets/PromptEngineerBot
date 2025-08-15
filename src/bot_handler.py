"""
Telegram bot message handlers and core logic.
"""

import logging

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes

from .config import BotConfig
from .conversation_manager import ConversationManager
from .llm_client_base import LLMClientBase
from .messages import (
    BTN_CRAFT,
    BTN_GGL,
    BTN_LYRA,
    BTN_LYRA_DETAIL,
    BTN_RESET,
    SELECT_METHOD_KEYBOARD,
    SELECT_METHOD_MESSAGE,
    WELCOME_MESSAGE,
    format_improved_prompt_response,
    get_processing_message,
    parse_llm_response,
)
from .prompt_loader import PromptLoader
from .state_manager import StateManager

logger = logging.getLogger(__name__)


class BotHandler:
    """Handles Telegram bot interactions and message processing."""

    def __init__(
        self, config: BotConfig, llm_client: LLMClientBase, sheets_logger_func=None
    ):
        self.config = config
        self.llm_client = llm_client
        self.state_manager = StateManager()
        self.conversation_manager = ConversationManager()
        self.prompt_loader = PromptLoader()
        self.log_sheets = sheets_logger_func or (lambda event, payload: None)

    def reset_user_state(self, user_id: int):
        """Reset the user's state and conversation history."""
        self.state_manager.set_waiting_for_prompt(user_id, True)
        self.state_manager.set_last_interaction(user_id, None)
        self.conversation_manager.reset(user_id)

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command or New Prompt button."""
        user_id = update.effective_user.id

        # TODO: probably don`t need to _log_conversation_totals here (why showing it in sheets??)
        # Log conversation totals before resetting if there was an ongoing conversation
        try:
            method_name = self.conversation_manager.get_current_method(user_id)
            self._log_conversation_totals(user_id, method_name)
        finally:
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

        # Handle prompt input
        if user_state.waiting_for_prompt:
            await self._handle_prompt_input(update, user_id, text)
            return

        # Handle method selection
        if self.conversation_manager.is_waiting_for_method(user_id):
            await self._handle_method_selection(update, user_id, text)
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

    async def _handle_method_selection(self, update: Update, user_id: int, text: str):
        """Handle optimization method selection."""
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

    async def _process_with_llm(self, update: Update, user_id: int, method_name: str):
        """Process conversation with LLM and handle response."""
        try:
            transcript = self.conversation_manager.get_transcript(user_id)
            raw_response = await self.llm_client.send_prompt(transcript)

            # Track token usage
            usage = self.llm_client.get_last_usage()
            self.conversation_manager.accumulate_token_usage(user_id, usage)

            # Parse response
            response, is_question, is_improved_prompt = parse_llm_response(raw_response)
            self.conversation_manager.append_message(user_id, "assistant", raw_response)

            if is_improved_prompt:
                # Store the optimized prompt before formatting
                optimized_prompt = response

                # Format final response and reset conversation
                user_prompt = self.conversation_manager.get_user_prompt(user_id)
                response = format_improved_prompt_response(
                    user_prompt, optimized_prompt, method_name
                )

                # Log conversation totals with only the optimized prompt
                self._log_conversation_totals(user_id, method_name, optimized_prompt)

                # Reset state
                self.conversation_manager.reset(user_id)
                self.state_manager.set_waiting_for_prompt(user_id, True)

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
        self, user_id: int, method_name: str, answer_text: str = None
    ):
        """Log conversation totals to sheets."""
        try:
            usage_totals = self.conversation_manager.get_token_totals(user_id)
            if not usage_totals or all(v == 0 for v in usage_totals.values()):
                return

            payload = {
                "BotID": self.config.bot_id or "UNKNOWN",
                "TelegramID": user_id,
                "LLM": f"{self.config.llm_backend}:{self.config.model_name}",
                "OptimizationModel": method_name,
                "UserRequest": self.conversation_manager.get_user_prompt(user_id) or "",
                "Answer": answer_text or "",
                **usage_totals,
            }
            self.log_sheets("conversation_totals", payload)
        except Exception as e:
            logger.error(f"Failed to log conversation totals: {e}", exc_info=True)

    async def _safe_reply(self, update: Update, text: str, **kwargs) -> bool:
        """Safely send a reply with error handling and length limits."""
        MAX_MESSAGE_LENGTH = 4096

        try:
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
                            raise e

                    # Only use special formatting and reply markup for first message
                    kwargs.pop("parse_mode", None)
                    kwargs.pop("reply_markup", None)
            else:
                await update.message.reply_text(text, **kwargs)
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")

            # If it's a Markdown parsing error, try without parse_mode
            if "parse entities" in str(e).lower() or "markdown" in str(e).lower():
                try:
                    # Remove parse_mode and try again
                    kwargs_no_parse = {
                        k: v for k, v in kwargs.items() if k != "parse_mode"
                    }
                    await update.message.reply_text(text, **kwargs_no_parse)
                    logger.info("Message sent successfully without Markdown parsing")
                    return True
                except Exception as e2:
                    logger.error(f"Failed to send message even without Markdown: {e2}")

            return False
