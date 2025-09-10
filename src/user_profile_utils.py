"""
User profile utilities for extracting and managing Telegram user profile data.

This module provides utilities for safely extracting user profile information
from Telegram Update objects and managing profile data updates.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from .database import User

logger = logging.getLogger(__name__)


def extract_user_profile(effective_user: Optional[Any]) -> Dict[str, Any]:
    """
    Extract user profile data from Telegram effective_user object.

    Safely extracts profile fields from update.effective_user, handling cases
    where fields are None or missing using getattr with appropriate defaults.

    Args:
        effective_user: Telegram User object from update.effective_user

    Returns:
        Dictionary containing extracted profile fields:
        - first_name: str or None
        - last_name: str or None
        - is_bot: bool (defaults to False)
        - is_premium: bool or None
        - language_code: str or None

    Requirements addressed:
        - 1.1: Extract first_name from update.effective_user.first_name
        - 1.2: Extract last_name from update.effective_user.last_name (handle null)
        - 1.3: Extract is_bot from update.effective_user.is_bot
        - 1.4: Extract is_premium from update.effective_user.is_premium (handle null)
        - 1.5: Extract language_code from update.effective_user.language_code (handle null)
        - 4.3: Handle cases where effective_user fields are None or missing
    """
    if effective_user is None:
        logger.debug("effective_user is None, returning empty profile data")
        return {
            "first_name": None,
            "last_name": None,
            "is_bot": False,
            "is_premium": None,
            "language_code": None,
        }

    try:
        # Extract profile data using getattr with safe defaults
        profile_data = {
            "first_name": getattr(effective_user, "first_name", None),
            "last_name": getattr(effective_user, "last_name", None),
            "is_bot": getattr(effective_user, "is_bot", False),
            "is_premium": getattr(effective_user, "is_premium", None),
            "language_code": getattr(effective_user, "language_code", None),
        }

        # Log successful extraction (with privacy considerations)
        logger.debug(
            f"Profile extracted: first_name={'present' if profile_data['first_name'] else 'None'}, "
            f"last_name={'present' if profile_data['last_name'] else 'None'}, "
            f"is_bot={profile_data['is_bot']}, "
            f"is_premium={profile_data['is_premium']}, "
            f"language_code={profile_data['language_code']}"
        )

        return profile_data

    except Exception as e:
        logger.error(f"Error extracting user profile data: {e}")
        # Return safe defaults on any extraction error
        return {
            "first_name": None,
            "last_name": None,
            "is_bot": False,
            "is_premium": None,
            "language_code": None,
        }


def has_meaningful_profile_changes(
    current_profile: Dict[str, Any], new_profile: Dict[str, Any]
) -> bool:
    """
    Check if profile has meaningful changes worth updating in the database.

    Compares current database profile values with new profile data to determine
    if an update is necessary. This helps avoid unnecessary database writes.

    Args:
        current_profile: Current profile data from database
        new_profile: New profile data from Telegram

    Returns:
        True if meaningful changes detected, False otherwise

    Note: This function supports the profile comparison utility mentioned in task 4,
    but is included here as it's closely related to profile extraction.
    """
    try:
        # Check for meaningful changes in profile fields
        meaningful_changes = (
            current_profile.get("first_name") != new_profile.get("first_name")
            or current_profile.get("last_name") != new_profile.get("last_name")
            or current_profile.get("is_premium") != new_profile.get("is_premium")
            or current_profile.get("language_code") != new_profile.get("language_code")
            # Note: is_bot typically doesn't change, but included for completeness
            # current_profile.get('is_bot') != new_profile.get('is_bot')
        )

        if meaningful_changes:
            logger.debug("Meaningful profile changes detected")
        else:
            logger.debug("No meaningful profile changes detected")

        return meaningful_changes

    except Exception as e:
        logger.error(f"Error comparing profile changes: {e}")
        # On error, assume changes exist to be safe
        return True


def should_update_user_profile(user: "User", effective_user: Optional[Any]) -> bool:
    """
    Profile comparison utility to determine if user profile should be updated.

    Compares current database profile with incoming Telegram profile data to
    determine if meaningful changes exist that warrant a database update.
    This is the main utility function for task 4.

    Args:
        user: User model instance with current database profile data
        effective_user: Telegram User object from update.effective_user

    Returns:
        bool: True if update is necessary, False otherwise

    Requirements addressed:
        - 4.2: Only update user profile data if significant changes are detected
        - 4.6: Compare current database values with update.effective_user values
    """
    try:
        # Extract new profile data from Telegram
        new_profile = extract_user_profile(effective_user)

        # Get current profile data from User model
        current_profile = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_bot": user.is_bot,
            "is_premium": user.is_premium,
            "language_code": user.language_code,
        }

        # Use existing comparison logic
        needs_update = has_meaningful_profile_changes(current_profile, new_profile)

        if needs_update:
            logger.debug(
                f"Profile update needed for user {user.telegram_id}: "
                f"current={current_profile}, new={new_profile}"
            )
        else:
            logger.debug(f"No profile update needed for user {user.telegram_id}")

        return needs_update

    except Exception as e:
        logger.error(
            f"Error determining if profile update needed for user {getattr(user, 'telegram_id', 'unknown')}: {e}"
        )
        # On error, assume update is needed to be safe
        return True
