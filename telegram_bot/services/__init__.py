"""
External service integrations.

This module contains integrations with external services including
LLM providers, email services, Redis, and Google Sheets.
"""

from telegram_bot.services.email_service import (
    get_email_service,
    init_email_service,
)
from telegram_bot.services.gsheets_logging import (
    build_google_sheets_handler_from_env,
)
from telegram_bot.services.redis_client import (
    get_redis_client,
    init_redis_client,
)

__all__ = [
    "get_email_service",
    "init_email_service",
    "build_google_sheets_handler_from_env",
    "get_redis_client",
    "init_redis_client",
]
