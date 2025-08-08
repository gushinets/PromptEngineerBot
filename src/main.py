"""
Telegram Prompt Engineering Bot

This bot helps users optimize their prompts using 
different methodologies (CRAFT, LYRA) by interacting 
with LLMs (OpenAI or OpenRouter).

Main responsibilities:
- Handle Telegram bot commands and messages
- Manage user state and conversation flow
- Load and select prompt optimization system prompts
- Send user/system prompts to LLM and return responses
"""

import logging
import json
import os
import asyncio
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.error import (
    NetworkError, 
    TimedOut, 
    BadRequest, 
    ChatMigrated, 
    RetryAfter
)
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

try:
    # When running as module: python -m src.main
    from src.state_manager import StateManager
    from src.openrouter_client import OpenRouterClient
    from src.messages import (
        WELCOME_MESSAGE, SELECT_METHOD_MESSAGE,
        SELECT_METHOD_KEYBOARD, get_processing_message,
        ERROR_EMPTY_MESSAGE, ERROR_GENERIC, ERROR_NETWORK, ERROR_RATE_LIMIT, ERROR_TOO_LONG,
        parse_llm_response, format_improved_prompt_response,
        BTN_RESET, BTN_CRAFT, BTN_LYRA, BTN_GGL, BTN_LYRA_DETAIL
    )
    from src.openai_client import OpenAIClient
    from src.conversation_manager import ConversationManager
    from src.gsheets_logging import build_google_sheets_handler_from_env
except ImportError:
    # When running directly: python src/main.py
    from state_manager import StateManager
    from openrouter_client import OpenRouterClient
    from messages import (
        WELCOME_MESSAGE, SELECT_METHOD_MESSAGE,
        SELECT_METHOD_KEYBOARD, get_processing_message,
        ERROR_EMPTY_MESSAGE, ERROR_GENERIC, ERROR_NETWORK, ERROR_RATE_LIMIT, ERROR_TOO_LONG,
        parse_llm_response, format_improved_prompt_response,
        BTN_RESET, BTN_CRAFT, BTN_LYRA, BTN_GGL, BTN_LYRA_DETAIL
    )
    from openai_client import OpenAIClient
    from conversation_manager import ConversationManager
    from gsheets_logging import build_google_sheets_handler_from_env

# Configure logging (keep internal logging to file/console unchanged)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load env early so Sheets handler sees variables from .env
load_dotenv()

# Dedicated Google Sheets logger (only for selected events)
_sheets_logger = None
try:
    _gsheets_handler = build_google_sheets_handler_from_env(os.getenv)
    if _gsheets_handler:
        _sheets_logger = logging.getLogger('sheets')
        _sheets_logger.setLevel(logging.INFO)
        _sheets_logger.propagate = False
        _sheets_logger.addHandler(_gsheets_handler)
        logger.info("Google Sheets logging enabled successfully")
    else:
        logger.warning("Google Sheets handler not created - check environment variables")
except Exception as e:
    # Do not fail if gsheets handler cannot be created
    logger.error(f"Failed to initialize Google Sheets logging: {e}", exc_info=True)
    _sheets_logger = None


def log_sheets(event: str, payload: dict) -> None:
    """Log a structured event to Google Sheets if enabled."""
    if not _sheets_logger or not _sheets_logger.handlers:
        logger.debug(f"Sheets logging disabled, skipping event: {event}")
        return
    try:
        message = json.dumps({"event": event, **payload}, ensure_ascii=False)
        _sheets_logger.info(message)
        logger.debug(f"Successfully logged to sheets: {event}")
    except Exception as e:
        logger.error(f"Failed to log to Google Sheets for event '{event}': {e}", exc_info=True)
        # Fallback to string format
        try:
            message = str({"event": event, **payload})
            _sheets_logger.info(message)
            logger.debug(f"Logged to sheets with fallback format: {event}")
        except Exception as e2:
            logger.error(f"Failed to log to sheets even with fallback format for event '{event}': {e2}")


def log_method_selection_to_file(user_id: int, trigger_text: str, method_name: str) -> None:
    """Log to bot.log when a user selects an optimization method."""
    try:
        logger.info(
            "method_selected | user_id=%s | method=%s | trigger=%s",
            user_id,
            method_name,
            trigger_text,
        )
    except Exception:
        # Best-effort logging; do not break flow
        pass


def _compose_llm_name() -> str:
    try:
        model_name = getattr(llm_client, 'model_name', None)
        return f"{llm_backend}:{model_name}" if model_name else llm_backend
    except Exception:
        return llm_backend


def log_llm_exchange_to_sheets(user_id: int, method_name: str, user_request: str, answer_text: str) -> None:
    """Emit a single structured row for an LLM exchange with token usage if available."""
    bot_id = _get_bot_identifier()
    usage = getattr(llm_client, 'last_usage', None) or {}
    payload = {
        "BotID": bot_id,
        "TelegramID": user_id,
        "LLM": _compose_llm_name(),
        "OptimizationModel": method_name,
        "UserRequest": user_request,
        "Answer": answer_text,
        "prompt_tokens": usage.get('prompt_tokens'),
        "completion_tokens": usage.get('completion_tokens'),
        "total_tokens": usage.get('total_tokens'),
    }
    log_sheets("llm_exchange", payload)


def log_conversation_totals_to_sheets(user_id: int, method_name: str, answer_text: str | None = None) -> None:
    """Log the aggregated token totals for the user's conversation to Google Sheets.
    If provided, include the improved prompt in the Answer field.
    """
    try:
        bot_id = _get_bot_identifier()
        usage_totals = conversation_manager.get_token_totals(user_id)
        # Skip if nothing accumulated
        if not usage_totals or (
            (usage_totals.get('prompt_tokens') or 0) == 0
            and (usage_totals.get('completion_tokens') or 0) == 0
            and (usage_totals.get('total_tokens') or 0) == 0
        ):
            logger.debug(f"No token usage to log for user {user_id}")
            return
        payload = {
            "BotID": bot_id,
            "TelegramID": user_id,
            "LLM": _compose_llm_name(),
            "OptimizationModel": method_name,
            # For totals rows, include original user prompt for context
            "UserRequest": conversation_manager.get_user_prompt(user_id) or "",
            "Answer": answer_text or "",
            "prompt_tokens": usage_totals.get('prompt_tokens'),
            "completion_tokens": usage_totals.get('completion_tokens'),
            "total_tokens": usage_totals.get('total_tokens'),
        }
        log_sheets("conversation_totals", payload)
    except Exception as e:
        # Best-effort logging; log errors for debugging
        logger.error(f"Failed to log conversation totals to sheets for user {user_id}: {e}", exc_info=True)


# Global bot identifier, set at startup; can be overridden with BOT_ID env
BOT_IDENTIFIER = os.getenv('BOT_ID')


def _parse_bot_id_from_token() -> str:
    token = os.getenv('TELEGRAM_TOKEN') or ''
    if ':' in token:
        candidate = token.split(':', 1)[0]
        if candidate.isdigit():
            return candidate
    return 'UNKNOWN'


def _get_bot_identifier() -> str:
    if BOT_IDENTIFIER:
        return BOT_IDENTIFIER
    # Fallback to numeric id from token if available
    return _parse_bot_id_from_token()

# Maximum number of retries for sending messages
MAX_RETRIES = 3

async def safe_reply(update: Update, text: str, **kwargs) -> bool:
    """
    Safely send a reply message with error handling and retries.
    
    Args:
        update: The update object from the Telegram bot
        text: The message text to send
        **kwargs: Additional arguments to pass to reply_text
        
    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    if not text or text.strip() == '':
        logger.warning("Attempted to send empty message")
        await update.message.reply_text(ERROR_EMPTY_MESSAGE)
        return False
    
    # Check message length (Telegram's limit is 4096 characters)
    if len(text) > 4000:  # Leave some room for potential formatting
        logger.warning(f"Message too long: {len(text)} characters")
        await update.message.reply_text(ERROR_TOO_LONG)
        return False
        
    for attempt in range(MAX_RETRIES):
        try:
            await update.message.reply_text(text, **kwargs)
            return True
            
        except RetryAfter as e:
            # Handle flood control limits
            wait_time = e.retry_after + 5  # Add some buffer time
            logger.warning(f"Rate limited. Waiting {wait_time} seconds before retry...")
            await update.message.reply_text(ERROR_RATE_LIMIT)
            await asyncio.sleep(wait_time)
            
        except TimedOut as e:
            logger.warning(f"Timeout while sending message (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt == MAX_RETRIES - 1:
                logger.error("Max retries reached. Giving up.")
                await update.message.reply_text(ERROR_NETWORK)
                return False
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
            
        except NetworkError as e:
            logger.error(f"Network error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt == MAX_RETRIES - 1:
                await update.message.reply_text(ERROR_NETWORK)
                return False
            await asyncio.sleep(2 ** attempt)
            
        except ChatMigrated as e:
            # Handle chat migration (supergroup migration)
            logger.warning(f"Chat migrated to {e.new_chat_id}")
            # You might want to update chat_id in your database here
            return False
            
        except BadRequest as e:
            logger.error(f"Bad request: {e}")
            if "message is too long" in str(e).lower():
                await update.message.reply_text(ERROR_TOO_LONG)
            else:
                await update.message.reply_text(ERROR_GENERIC)
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            if attempt == MAX_RETRIES - 1:
                try:
                    await update.message.reply_text(ERROR_GENERIC)
                except Exception:
                    pass
                return False
            # Retry after brief backoff
            await asyncio.sleep(2 ** attempt)
            continue
    
    return False

# Load environment variables
load_dotenv()

# Debug: Log environment variables
logger.info("Environment variables loaded. Checking required variables...")
required_vars = ['TELEGRAM_TOKEN', 'LLM_BACKEND']
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
else:
    logger.info("All required environment variables are present.")
    logger.debug(f"LLM_BACKEND: {os.getenv('LLM_BACKEND')}")
    # Don't log tokens for security
    logger.debug("TELEGRAM_TOKEN present: Yes")

# --- PROMPT LOADING ---
def load_prompt(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), 'prompts')
CRAFT_PROMPT_PATH = os.path.join(PROMPTS_DIR, 'CRAFT_prompt.txt')
LYRA_PROMPT_PATH = os.path.join(PROMPTS_DIR, 'LYRA_prompt.txt')
GGL_PROMPT_PATH = os.path.join(PROMPTS_DIR, 'GGL_prompt.txt')

craft_prompt = load_prompt(CRAFT_PROMPT_PATH)
lyra_prompt = load_prompt(LYRA_PROMPT_PATH)
ggl_prompt = load_prompt(GGL_PROMPT_PATH)

# Button constants and keyboards are imported from messages.py

state_manager = StateManager()
conversation_manager = ConversationManager()


# Select LLM backend
llm_backend = os.getenv('LLM_BACKEND', 'OPENROUTER').upper()
if llm_backend == 'OPENAI':
    llm_client = OpenAIClient(
        api_key=os.getenv('OPENAI_API_KEY'),
        model_name=os.getenv('MODEL_NAME', 'gpt-4o'),
        max_retries=5,  # Increased from default 3 to 5
        request_timeout=60.0,  # 60 seconds per request
        max_wait_time=300.0  # 5 minutes total including retries
    )
else:
    llm_client = OpenRouterClient(
        api_key=os.getenv('OPENROUTER_API_KEY'),
        model_name=os.getenv('MODEL_NAME', 'openai/gpt-4')
    )


# Keyboard is now defined in messages.py

def reset_user_state(user_id: int):
    """
    Reset the user's state and conversation history.
    
    Args:
        user_id: The ID of the user whose state should be reset
    """
    state_manager.set_waiting_for_prompt(user_id, True)
    state_manager.set_last_interaction(user_id, None)
    conversation_manager.reset(user_id)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command or New Prompt button."""
    user_id = update.effective_user.id
    # If there was an ongoing conversation, log its totals before resetting
    try:
        method_name = conversation_manager.get_current_method(user_id)
        log_conversation_totals_to_sheets(user_id, method_name)
    finally:
        reset_user_state(user_id)
    
    # Send welcome message
    await safe_reply(
        update,
        WELCOME_MESSAGE,
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True)
    )

    # Sheets: log session start
    log_sheets("session_start", {"user_id": user_id})
    

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    user_state = state_manager.get_user_state(user_id)

    # If user presses reset button, always reset the conversation
    if text == BTN_RESET:
        await start(update, context)
        return

    # If waiting for prompt
    if user_state.waiting_for_prompt:
        conversation_manager.reset(user_id)
        conversation_manager.set_user_prompt(user_id, text)
        conversation_manager.append_message(user_id, "user", text)  # Store user prompt
        conversation_manager.set_waiting_for_method(user_id, True)
        user_state.waiting_for_prompt = False

        # Sheets: log prompt received (truncated)
        log_sheets("prompt_received", {"user_id": user_id, "length": len(text), "preview": text[:120]})
        
        # Add reset button to the method selection keyboard
        method_keyboard = list(SELECT_METHOD_KEYBOARD.keyboard)
        method_keyboard.append([BTN_RESET])
        await safe_reply(
            update,
            SELECT_METHOD_MESSAGE,
            reply_markup=ReplyKeyboardMarkup(method_keyboard, resize_keyboard=True)
        )
        return

    # If waiting for method selection
    if conversation_manager.is_waiting_for_method(user_id):
        transcript = conversation_manager.get_transcript(user_id)
        if text == BTN_CRAFT:
            log_method_selection_to_file(user_id, text, "CRAFT")
            log_sheets("method_selected", {"user_id": user_id, "method": "CRAFT"})
            # Insert system prompt at the start if not present
            if not transcript or transcript[0]["role"] != "system":
                transcript.insert(0, {"role": "system", "content": craft_prompt})
            conversation_manager.set_waiting_for_method(user_id, False)
            conversation_manager.set_current_method(user_id, "CRAFT")
            # Send processing message with method name
            await update.message.reply_text(
                get_processing_message("craft"),
                parse_mode='Markdown'
            )
            try:
                raw_response = await llm_client.send_prompt(transcript)
                # Accumulate token usage for this turn
                conversation_manager.accumulate_token_usage(user_id, getattr(llm_client, 'last_usage', None))
                response, is_question, is_improved_prompt = parse_llm_response(raw_response)
                conversation_manager.append_message(user_id, "assistant", raw_response)
                
                if is_improved_prompt:
                    # Format the improved prompt response
                    user_prompt = conversation_manager.get_user_prompt(user_id)
                    method_name = "CRAFT"
                    improved_prompt_only = response
                    response = format_improved_prompt_response(user_prompt, improved_prompt_only, method_name)
                    # Log aggregated totals at conversation end (include improved prompt)
                    log_conversation_totals_to_sheets(user_id, method_name, improved_prompt_only)
                    # Reset conversation after sending improved prompt
                    conversation_manager.reset(user_id)
                    # Reset the user state using the state manager
                    state_manager.set_waiting_for_prompt(user_id, True)
                
                await safe_reply(
                    update,
                    response,
                    parse_mode='Markdown',
                    reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True)
                )
            except Exception as e:
                logger.error(f"Error in CRAFT processing: {e}", exc_info=True)
                log_sheets("error", {"stage": "CRAFT", "user_id": user_id, "error": str(e)})
                await safe_reply(
                    update,
                    f"{ERROR_GENERIC}\n\n{str(e)}",
                    reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True)
                )
            return
        elif text == BTN_LYRA:
            log_method_selection_to_file(user_id, text, "LYRA Basic")
            log_sheets("method_selected", {"user_id": user_id, "method": "LYRA Basic"})
            # Insert LYRA system prompt if not present
            if not transcript or transcript[0]["role"] != "system":
                transcript.insert(0, {"role": "system", "content": lyra_prompt})
            conversation_manager.append_message(user_id, "user", "BASIC using ChatGPT")
            conversation_manager.set_waiting_for_method(user_id, False)
            conversation_manager.set_current_method(user_id, "LYRA Basic")
            # Send processing message with method name
            await update.message.reply_text(
                get_processing_message("lyra"),
                parse_mode='Markdown'
            )
            try:
                raw_response = await llm_client.send_prompt(transcript)
                # Accumulate token usage for this turn
                conversation_manager.accumulate_token_usage(user_id, getattr(llm_client, 'last_usage', None))
                response, is_question, is_improved_prompt = parse_llm_response(raw_response)
                conversation_manager.append_message(user_id, "assistant", raw_response)
                
                if is_improved_prompt:
                    # Format the improved prompt response
                    user_prompt = conversation_manager.get_user_prompt(user_id)
                    method_name = "LYRA"
                    improved_prompt_only = response
                    response = format_improved_prompt_response(user_prompt, improved_prompt_only, method_name)
                    # Log aggregated totals at conversation end (include improved prompt)
                    log_conversation_totals_to_sheets(user_id, method_name, improved_prompt_only)
                    # Reset conversation after logging totals
                    conversation_manager.reset(user_id)
                    # Reset the user state using the state manager
                    state_manager.set_waiting_for_prompt(user_id, True)
                
                await safe_reply(
                    update,
                    response,
                    parse_mode='Markdown',
                    reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True)
                )
            except Exception as e:
                error_msg = f"Ошибка: {e}"
                conversation_manager.append_message(user_id, "assistant", error_msg)
                log_sheets("error", {"stage": "LYRA Basic", "user_id": user_id, "error": str(e)})
                await safe_reply(
                    update,
                    error_msg,
                    reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True)
                )
            return
        elif text == BTN_LYRA_DETAIL:
            log_method_selection_to_file(user_id, text, "LYRA Detail")
            log_sheets("method_selected", {"user_id": user_id, "method": "LYRA Detail"})
            # Insert LYRA system prompt if not present
            if not transcript or transcript[0]["role"] != "system":
                transcript.insert(0, {"role": "system", "content": lyra_prompt})
            conversation_manager.append_message(user_id, "user", "DETAILED using ChatGPT")
            conversation_manager.set_waiting_for_method(user_id, False)
            conversation_manager.set_current_method(user_id, "LYRA Detail")
            # Send processing message with method name
            await update.message.reply_text(
                get_processing_message("lyra_detail"),
                parse_mode='Markdown'
            )
            try:
                raw_response = await llm_client.send_prompt(transcript)
                # Accumulate token usage for this turn
                conversation_manager.accumulate_token_usage(user_id, getattr(llm_client, 'last_usage', None))
                response, is_question, is_improved_prompt = parse_llm_response(raw_response)
                conversation_manager.append_message(user_id, "assistant", raw_response)
                
                if is_improved_prompt:
                    # Format the improved prompt response
                    user_prompt = conversation_manager.get_user_prompt(user_id)
                    method_name = "LYRA"
                    improved_prompt_only = response
                    response = format_improved_prompt_response(user_prompt, improved_prompt_only, method_name)
                    # Log aggregated totals at conversation end (include improved prompt)
                    log_conversation_totals_to_sheets(user_id, method_name, improved_prompt_only)
                    # Reset conversation after logging totals
                    conversation_manager.reset(user_id)
                    # Reset the user state using the state manager
                    state_manager.set_waiting_for_prompt(user_id, True)
                
                await safe_reply(
                    update,
                    response,
                    parse_mode='Markdown',
                    reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True)
                )
            except Exception as e:
                error_msg = f"Ошибка: {e}"
                conversation_manager.append_message(user_id, "assistant", error_msg)
                log_sheets("error", {"stage": "LYRA Detail", "user_id": user_id, "error": str(e)})
                await safe_reply(
                    update,
                    error_msg,
                    reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True)
                )
            return
        elif text == BTN_GGL:
            log_method_selection_to_file(user_id, text, "GGL")
            log_sheets("method_selected", {"user_id": user_id, "method": "GGL"})
            # Insert GGL system prompt if not present
            if not transcript or transcript[0]["role"] != "system":
                transcript.insert(0, {"role": "system", "content": ggl_prompt})
            conversation_manager.set_waiting_for_method(user_id, False)
            conversation_manager.set_current_method(user_id, "GGL")
            # Send processing message with method name
            await update.message.reply_text(
                get_processing_message("ggl"),
                parse_mode='Markdown'
            )
            try:
                raw_response = await llm_client.send_prompt(transcript)
                # Accumulate token usage for this turn
                conversation_manager.accumulate_token_usage(user_id, getattr(llm_client, 'last_usage', None))
                response, is_question, is_improved_prompt = parse_llm_response(raw_response)
                conversation_manager.append_message(user_id, "assistant", raw_response)
                
                if is_improved_prompt:
                    # Format the improved prompt response
                    user_prompt = conversation_manager.get_user_prompt(user_id)
                    method_name = "GGL"
                    improved_prompt_only = response
                    response = format_improved_prompt_response(user_prompt, improved_prompt_only, method_name)
                    # Log aggregated totals at conversation end (include improved prompt)
                    log_conversation_totals_to_sheets(user_id, method_name, improved_prompt_only)
                    # Reset conversation after logging totals
                    conversation_manager.reset(user_id)
                    # Reset the user state using the state manager
                    state_manager.set_waiting_for_prompt(user_id, True)
                
                await safe_reply(
                    update,
                    response,
                    parse_mode='Markdown',
                    reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True)
                )
            except Exception as e:
                error_msg = f"Ошибка: {e}"
                conversation_manager.append_message(user_id, "assistant", error_msg)
                log_sheets("error", {"stage": "GGL", "user_id": user_id, "error": str(e)})
                await safe_reply(
                    update,
                    error_msg,
                    reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True)
                )
            return
        else:
            # Add reset button to the method selection keyboard
            method_keyboard = list(SELECT_METHOD_KEYBOARD.keyboard)
            method_keyboard.append([BTN_RESET])
            await safe_reply(
                update,
                SELECT_METHOD_MESSAGE,
                reply_markup=ReplyKeyboardMarkup(method_keyboard, resize_keyboard=True)
            )
            return

    # This check is now at the beginning of the function

    # Multi-turn: continue conversation with full transcript
    transcript = conversation_manager.get_transcript(user_id)
    conversation_manager.append_message(user_id, "user", text)
    try:
        raw_response = await llm_client.send_prompt(transcript)
        # Accumulate token usage for this turn
        conversation_manager.accumulate_token_usage(user_id, getattr(llm_client, 'last_usage', None))
        response, is_question, is_improved_prompt = parse_llm_response(raw_response)
        conversation_manager.append_message(user_id, "assistant", raw_response)
        
        if is_improved_prompt:
            # Format the improved prompt response
            user_prompt = conversation_manager.get_user_prompt(user_id)
            method_name = conversation_manager.get_current_method(user_id)
            improved_prompt_only = response
            response = format_improved_prompt_response(user_prompt, improved_prompt_only, method_name)
            # Log aggregated totals at conversation end (include improved prompt)
            log_conversation_totals_to_sheets(user_id, method_name, improved_prompt_only)
            # Reset user state after logging totals
            reset_user_state(user_id)
        
        await safe_reply(
            update,
            response,
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True)
        )
    except Exception as e:
        error_msg = f"Ошибка: {e}"
        conversation_manager.append_message(user_id, "assistant", error_msg)
        log_sheets("error", {"stage": "multi_turn", "user_id": user_id, "error": str(e)})
        await safe_reply(
            update,
            error_msg,
            reply_markup=ReplyKeyboardMarkup([[BTN_RESET]], resize_keyboard=True)
        )

async def main():
    """Start the bot."""
    # Get the token
    token = os.getenv('TELEGRAM_TOKEN')
    if not token:
        logger.error("TELEGRAM_TOKEN environment variable is not set!")
        return

    logger.info("Starting bot with token: {}...".format(token[:5] + '...' + token[-5:]))
    
    try:
        # Create the Application with connection pool settings
        # Increased timeouts to handle slow LLM responses and poor connections
        application = (
            Application.builder()
            .token(token)
            .connect_timeout(60.0)      # Increased from 30s to 60s for initial connection
            .pool_timeout(60.0)         # Increased from 30s to 60s for connection pool
            .read_timeout(300.0)        # Increased from 30s to 300s (5 min) for LLM responses
            .write_timeout(120.0)       # Increased from 30s to 120s for sending data
            .get_updates_read_timeout(60.0)  # Specific timeout for getUpdates polling
            .pool_timeout(60.0)         # Timeout for getting a connection from the pool
            .build()
        )

        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        # Start the Bot with error handling
        logger.info("Starting polling...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        logger.info("Bot is running. Press Ctrl+C to stop.")
        
        # Keep the application running
        while True:
            await asyncio.sleep(1)
            
    except asyncio.CancelledError:
        logger.info("Shutting down...")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        raise
    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}")
        logger.exception("Exception details:")
        raise

if __name__ == '__main__':
    import asyncio
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.exception("Exception details:")
        raise


