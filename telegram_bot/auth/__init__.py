"""
Authentication and user management.

This module contains authentication services and user profile utilities.
"""

from telegram_bot.auth.auth_service import (
    get_auth_service,
    init_auth_service,
)
from telegram_bot.auth.user_profile_utils import (
    extract_user_profile,
    has_meaningful_profile_changes,
    should_update_user_profile,
)


__all__ = [
    "extract_user_profile",
    "get_auth_service",
    "has_meaningful_profile_changes",
    "init_auth_service",
    "should_update_user_profile",
]
