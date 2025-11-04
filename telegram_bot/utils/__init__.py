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
    SELECT_METHOD_MESSAGE,
    WELCOME_MESSAGE,
    get_processing_message,
)
from telegram_bot.utils.metrics import (
    get_metrics_collector,
    init_metrics_collector,
)
from telegram_bot.utils.prompt_loader import PromptLoader

__all__ = [
    "get_audit_service",
    "init_audit_service",
    "BotConfig",
    "EmailTemplates",
    "get_degradation_manager",
    "init_degradation_manager",
    "get_health_monitor",
    "init_health_monitor",
    "setup_application_logging",
    "WELCOME_MESSAGE",
    "SELECT_METHOD_MESSAGE",
    "get_processing_message",
    "get_metrics_collector",
    "init_metrics_collector",
    "PromptLoader",
]
