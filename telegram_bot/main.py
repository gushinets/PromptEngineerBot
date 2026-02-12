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
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from telegram_bot.core.bot_handler import BotHandler
from telegram_bot.data.database import init_database_from_config
from telegram_bot.flows.background_tasks import (
    init_background_tasks,
    start_background_tasks,
    stop_background_tasks,
)
from telegram_bot.services.gsheets_logging import build_google_sheets_handler_from_env
from telegram_bot.services.llm.factory import LLMClientFactory

# NOTE: Specific message constants are imported where needed inside handlers
from telegram_bot.services.redis_client import get_redis_client, init_redis_client
from telegram_bot.utils.config import BotConfig
from telegram_bot.utils.graceful_degradation import init_degradation_manager
from telegram_bot.utils.health_checks import init_health_monitor
from telegram_bot.utils.logging_utils import setup_application_logging


# Load env early so Sheets handler sees variables from .env
load_dotenv()

# Centralized logging with PII-protected formatting and quieter third-party libs
setup_application_logging(log_level=os.getenv("LOG_LEVEL", "INFO"))


# Optional file logging (disabled by default in containers)
def _maybe_add_file_logging() -> None:
    """
    Optionally add a file handler if explicitly enabled via environment.

    This avoids permission issues in containers and keeps the default logging
    directed to stdout/stderr for Docker log collectors.

    Environment variables:
    - LOG_TO_FILE: enable file logging when set to true/1/yes
    - LOG_FILE_PATH: path to the log file (default: bot.log)
    """
    log_to_file = os.getenv("LOG_TO_FILE", "").lower() in ("true", "1", "yes")
    if not log_to_file:
        return

    log_file_path = os.getenv("LOG_FILE_PATH", "bot.log")
    try:
        file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logging.getLogger().addHandler(file_handler)
        logging.getLogger("application").info(
            "FILE_LOGGING_ENABLED: Writing logs to file: %s", log_file_path
        )
    except Exception as e:
        logging.getLogger("application").warning(
            "FILE_LOGGING_DISABLED: Could not add file handler: %s", str(e)
        )


_maybe_add_file_logging()
logger = logging.getLogger(__name__)

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
        logger.warning("Google Sheets handler not created - check environment variables")
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
        logger.error(f"Failed to log to Google Sheets for event '{event}': {e}", exc_info=True)
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

# Email flow orchestrator will be initialized later in main() after all services are ready

# Create bot handler
bot_handler = BotHandler(config, llm_client, log_sheets)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command or New Prompt button."""
    await bot_handler.handle_start(update, context)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages from users."""
    
    await bot_handler.handle_message(update, context)


async def handle_followup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks for follow-up choice (YES/NO).

    This handler processes callback queries from the inline buttons attached
    to the follow-up offer message.

    Requirements: 8.4
    """
    await bot_handler.handle_followup_callback(update, context)


async def handle_disabled_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle clicks on disabled inline buttons (no-op handler).

    This handler simply answers the callback query to remove the loading
    indicator when users click on already-disabled buttons.

    Requirements: 8.4
    """
    query = update.callback_query
    await query.answer()


async def main():
    """Start the bot."""
    # Get the token
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN environment variable is not set!")
        return

    logger.info("Starting bot with token: {}...".format(token[:5] + "..." + token[-5:]))

    # Initialize graceful degradation manager
    language = os.getenv("LANGUAGE", "EN")
    _degradation_manager = init_degradation_manager(language)
    logger.info(f"Graceful degradation manager initialized with language: {language}")

    # Initialize email feature components
    health_monitor = None
    background_scheduler = None

    try:
        # Initialize database (if email feature is enabled)
        if config.email_enabled:
            logger.info("Initializing email feature components...")

            # Initialize database
            init_database_from_config(config)
            logger.info("Database initialized successfully")

            # Initialize Redis client
            init_redis_client(config)
            logger.info("Redis client initialized successfully")
            # Verify Redis write capability to avoid read-only replica misconfigurations
            try:
                if not get_redis_client().health_check():
                    message = "Redis health (write) check failed. Ensure REDIS_URL points to a writable primary."
                    if config.redis_write_check_strict:
                        logger.error(message)
                        raise RuntimeError("Redis write health check failed")
                    logger.warning(message)
            except Exception as redis_init_err:
                logger.error(f"Redis initialization/health verification failed: {redis_init_err}")
                raise

            # Initialize auth service
            from telegram_bot.auth.auth_service import init_auth_service

            init_auth_service(config)
            logger.info("Auth service initialized successfully")

            # Initialize user tracking service
            from telegram_bot.services.user_tracking import init_user_tracking_service

            user_tracking_service = init_user_tracking_service()
            bot_handler.set_user_tracking_service(user_tracking_service)
            logger.info("User tracking service initialized successfully")

            # Initialize session service for session tracking
            from telegram_bot.dependencies import get_container

            session_service = get_container().get_session_service()
            bot_handler.set_session_service(session_service)
            logger.info("Session service initialized successfully")

            # Initialize audit service
            from telegram_bot.utils.audit_service import init_audit_service

            init_audit_service()
            logger.info("Audit service initialized successfully")

            # Initialize health monitoring
            health_monitor = init_health_monitor(config)
            logger.info("Health monitor initialized successfully")

            # Start health monitoring
            await health_monitor.start_monitoring(check_interval=30)
            logger.info("Health monitoring started")

            # Initialize and start background tasks
            background_scheduler = init_background_tasks()
            start_background_tasks()
            logger.info("Background tasks started")

            # Initialize email service
            from telegram_bot.services.email_service import init_email_service

            init_email_service(config)
            logger.info("Email service initialized successfully")

            # Initialize email flow orchestrator after all services are ready
            from telegram_bot.flows.email_flow import init_email_flow_orchestrator

            # Initialize email flow orchestrator using shared dependencies
            orchestrator = init_email_flow_orchestrator(
                config,
                llm_client,
            )

            # Set the orchestrator on the bot handler
            bot_handler.set_email_flow_orchestrator(orchestrator)
            logger.info("Email flow orchestrator initialized successfully")
        else:
            logger.info("Email feature disabled - skipping email component initialization")

        # Create the Application with connection pool settings
        # Increased timeouts to handle slow LLM responses and poor connections
        application = (
            Application.builder()
            .token(token)
            .connect_timeout(30.0)  # Connection timeout for initial TCP connection
            .pool_timeout(10.0)  # Timeout for getting a connection from the pool
            .read_timeout(300.0)  # Read timeout for LLM responses (5 min)
            .write_timeout(60.0)  # Write timeout for sending data
            .get_updates_read_timeout(
                42.0
            )  # Telegram long polling timeout (slightly longer than server's 40s)
            .build()
        )

        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(
    MessageHandler((filters.TEXT | filters.VOICE) & ~filters.COMMAND, handle_message)
)


        # Add callback query handlers for follow-up inline buttons
        # Handler for follow-up choice buttons (YES/NO)
        application.add_handler(
            CallbackQueryHandler(handle_followup_callback, pattern="^followup_(yes|no)$")
        )
        # Handler for disabled button clicks (no-op)
        application.add_handler(
            CallbackQueryHandler(handle_disabled_callback, pattern="^disabled$")
        )
        logger.info("Callback handlers registered for follow-up inline buttons")

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

        # Stop background services
        if health_monitor:
            await health_monitor.stop_monitoring()
            logger.info("Health monitoring stopped")

        if background_scheduler:
            stop_background_tasks()
            logger.info("Background tasks stopped")

        # Stop Telegram bot
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        logger.info("Bot shutdown complete")
        raise
    except Exception as e:
        logger.error(f"Failed to start bot: {e!s}")
        logger.exception("Exception details:")

        # Cleanup on error
        if health_monitor:
            try:
                await health_monitor.stop_monitoring()
            except Exception as cleanup_error:
                logger.error(f"Error stopping health monitor: {cleanup_error}")

        if background_scheduler:
            try:
                stop_background_tasks()
            except Exception as cleanup_error:
                logger.error(f"Error stopping background tasks: {cleanup_error}")

        raise


if __name__ == "__main__":
    import asyncio

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e!s}")
        logger.exception("Exception details:")
        raise
