"""
Telegram Prompt Engineering Bot

A Telegram bot that helps users optimize their prompts using various
optimization methods (CRAFT, LYRA, GGL).
"""

__version__ = "1.0.0"
__author__ = "Prompt Engineering Bot Team"
__license__ = "MIT"
__description__ = "A Telegram bot for prompt engineering optimization"

# Public API exports
from telegram_bot.core.bot_handler import BotHandler
from telegram_bot.data.database import init_database_from_config
from telegram_bot.services.llm.factory import LLMClientFactory
from telegram_bot.utils.config import BotConfig

__all__ = [
    "BotHandler",
    "BotConfig",
    "LLMClientFactory",
    "init_database_from_config",
    "__version__",
    "__author__",
    "__license__",
    "__description__",
]
