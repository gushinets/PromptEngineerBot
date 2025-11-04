"""
Data access layer.

This module contains database connection management and data models.
"""

from telegram_bot.data.database import (
    get_db_session,
    init_database_from_config,
)

__all__ = [
    "get_db_session",
    "init_database_from_config",
]
