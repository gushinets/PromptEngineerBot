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

from .messages import (
    ERROR_EMPTY_MESSAGE, ERROR_GENERIC, ERROR_NETWORK, ERROR_RATE_LIMIT, ERROR_TOO_LONG
)
from .gsheets_logging import build_google_sheets_handler_from_env

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

# Initialize configuration and components
from .config import BotConfig
from .llm_factory import LLMClientFactory
from .bot_handler import BotHandler

# Load and validate configuration
config = BotConfig.from_env()
config.validate()

logger.info("Configuration loaded successfully")
logger.info(f"LLM Backend: {config.llm_backend}")
logger.info(f"Model: {config.model_name}")

# Create LLM client
llm_client = LLMClientFactory.create_client(config)

# Create bot handler
bot_handler = BotHandler(config, llm_client, log_sheets)


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
    await bot_handler.handle_start(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages from users."""
    await bot_handler.handle_message(update, context)

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


