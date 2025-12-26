"""
Shared utilities and helpers.

This module contains configuration, logging, metrics, health checks,
and other utility functions used across the application.
"""

from telegram_bot.utils.audit_service import (
    get_audit_service,
    init_audit_service,
)
from telegram_bot.utils.config import BotConfig
from telegram_bot.utils.email_templates import EmailTemplates
from telegram_bot.utils.graceful_degradation import (
    get_degradation_manager,
    init_degradation_manager,
)
from telegram_bot.utils.health_checks import (
    get_health_monitor,
    init_health_monitor,
)
from telegram_bot.utils.logging_utils import setup_application_logging
from telegram_bot.utils.messages import (
    BTN_SUPPORT,
    SELECT_METHOD_MESSAGE,
    SUPPORT_KEYBOARD,
    # WELCOME_MESSAGE is deprecated but kept for backward compatibility
    # until bot_handler.py and tests are updated (tasks 3, 5, 6)
    WELCOME_MESSAGE,
    WELCOME_MESSAGE_1,
    WELCOME_MESSAGE_2,
    get_processing_message,
)
from telegram_bot.utils.metrics import (
    get_metrics_collector,
    init_metrics_collector,
)
from telegram_bot.utils.prompt_loader import PromptLoader


__all__ = [
    "BTN_SUPPORT",
    "SELECT_METHOD_MESSAGE",
    "SUPPORT_KEYBOARD",
    # WELCOME_MESSAGE is deprecated - remove after tasks 3, 5, 6 are complete
    "WELCOME_MESSAGE",
    "WELCOME_MESSAGE_1",
    "WELCOME_MESSAGE_2",
    "BotConfig",
    "EmailTemplates",
    "PromptLoader",
    "get_audit_service",
    "get_degradation_manager",
    "get_health_monitor",
    "get_metrics_collector",
    "get_processing_message",
    "init_audit_service",
    "init_degradation_manager",
    "init_health_monitor",
    "init_metrics_collector",
    "setup_application_logging",
]
