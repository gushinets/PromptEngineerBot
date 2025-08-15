"""
Telegram Prompt Engineering Bot

This bot helps users optimize their prompts using
different methodologies (CRAFT, LYRA) by interacting
with LLMs (OpenAI or OpenRouter).

Main responsibilities:
- Application bootstrap and configuration
- Telegram bot initialization and lifecycle management
- High-level coordination between components
"""

import asyncio
import json
import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .bot_handler import BotHandler
from .config import BotConfig
from .gsheets_logging import build_google_sheets_handler_from_env
from .llm_factory import LLMClientFactory
from .messages import (
    ERROR_EMPTY_MESSAGE,
    ERROR_GENERIC,
    ERROR_NETWORK,
    ERROR_RATE_LIMIT,
    ERROR_TOO_LONG,
)

# Configure logging (keep internal logging to file/console unchanged)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Load env early so Sheets handler sees variables from .env
load_dotenv()

# Dedicated Google Sheets logger (only for selected events)
_sheets_logger = None
try:
    _gsheets_handler = build_google_sheets_handler_from_env(os.getenv)
    if _gsheets_handler:
        _sheets_logger = logging.getLogger("sheets")
        _sheets_logger.setLevel(logging.INFO)
        _sheets_logger.propagate = False
        _sheets_logger.addHandler(_gsheets_handler)
        logger.info("Google Sheets logging enabled successfully")
    else:
        logger.warning(
            "Google Sheets handler not created - check environment variables"
        )
except Exception as e:
    # Do not fail if gsheets handler cannot be created
    logger.error(f"Failed to initialize Google Sheets logging: {e}", exc_info=True)
    _sheets_logger = None


def log_sheets(event: str, payload: dict) -> None:
    """Log only conversation_totals events to Google Sheets. All other events are logged to bot.log only."""
    # Only log conversation_totals events to Google Sheets
    if event != "conversation_totals":
        logger.debug(
            f"Event '{event}' not logged to sheets - only conversation_totals are logged to sheets"
        )
        return

    if not _sheets_logger or not _sheets_logger.handlers:
        logger.debug(f"Sheets logging disabled, skipping event: {event}")
        return
    try:
        message = json.dumps({"event": event, **payload}, ensure_ascii=False)
        _sheets_logger.info(message)
        logger.debug(f"Successfully logged to sheets: {event}")
    except Exception as e:
        logger.error(
            f"Failed to log to Google Sheets for event '{event}': {e}", exc_info=True
        )
        # Fallback to string format
        try:
            message = str({"event": event, **payload})
            _sheets_logger.info(message)
            logger.debug(f"Logged to sheets with fallback format: {event}")
        except Exception as e2:
            logger.error(
                f"Failed to log to sheets even with fallback format for event '{event}': {e2}"
            )


# Initialize configuration and components

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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command or New Prompt button."""
    await bot_handler.handle_start(update, context)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages from users."""
    await bot_handler.handle_message(update, context)


async def main():
    """Start the bot."""
    # Get the token
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN environment variable is not set!")
        return

    logger.info("Starting bot with token: {}...".format(token[:5] + "..." + token[-5:]))

    try:
        # Create the Application with connection pool settings
        # Increased timeouts to handle slow LLM responses and poor connections
        application = (
            Application.builder()
            .token(token)
            .connect_timeout(60.0)  # Increased from 30s to 60s for initial connection
            .pool_timeout(60.0)  # Increased from 30s to 60s for connection pool
            .read_timeout(300.0)  # Increased from 30s to 300s (5 min) for LLM responses
            .write_timeout(120.0)  # Increased from 30s to 120s for sending data
            .get_updates_read_timeout(60.0)  # Specific timeout for getUpdates polling
            .pool_timeout(60.0)  # Timeout for getting a connection from the pool
            .build()
        )

        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        )

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


if __name__ == "__main__":
    import asyncio

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.exception("Exception details:")
        raise
