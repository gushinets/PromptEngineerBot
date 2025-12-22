"""
External service integrations.

This module contains integrations with external services including
LLM providers, email services, Redis, Google Sheets, and session tracking.
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
from telegram_bot.services.session_service import (
    OptimizationMethod,
    SessionService,
    SessionStatus,
    get_session_service,
    init_session_service,
)


__all__ = [
    "OptimizationMethod",
    "SessionService",
    "SessionStatus",
    "build_google_sheets_handler_from_env",
    "get_email_service",
    "get_redis_client",
    "get_session_service",
    "init_email_service",
    "init_redis_client",
    "init_session_service",
]
