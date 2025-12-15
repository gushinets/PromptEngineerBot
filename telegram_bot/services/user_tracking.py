"""
User tracking service for managing user lifecycle and activity timestamps.

This module provides the UserTrackingService class that handles:
- Creating users on first bot interaction (before email verification)
- Tracking first and last interaction timestamps
- Detecting first-time vs returning users
- Updating user profile data when changes are detected

The service integrates with existing user profile utilities and follows
the same patterns as AuthService for consistency.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError

from telegram_bot.auth.user_profile_utils import (
    extract_user_profile,
    should_update_user_profile,
)
from telegram_bot.data.database import (
    User,
    get_db_session,
    mask_telegram_id,
)


logger = logging.getLogger(__name__)


class UserTrackingService:
    """
    Service for tracking user interactions and managing user lifecycle.

    This service handles:
    - Creating user records on first bot interaction (before email verification)
    - Tracking first_interaction_at and last_interaction_at timestamps
    - Identifying first-time users vs returning users
    - Updating user profile data when meaningful changes are detected

    The service uses existing utilities from user_profile_utils.py:
    - extract_user_profile: For extracting Telegram profile data
    - should_update_user_profile: For detecting profile changes
    """

    def __init__(self) -> None:
        """
        Initialize the UserTrackingService.

        Database sessions are managed per-operation using get_db_session()
        context manager, following the same pattern as AuthService.
        """
        logger.debug("UserTrackingService initialized")

    def get_or_create_user(
        self,
        telegram_id: int,
        effective_user: Any | None,
    ) -> tuple[User | None, bool]:
        """
        Get existing user or create new one.

        For new users:
        - Creates user with email=null and is_authenticated=false
        - Sets first_interaction_at and last_interaction_at to current UTC time
        - Extracts and stores profile data using extract_user_profile

        For existing users:
        - Returns the existing user record without modification

        Args:
            telegram_id: User's Telegram ID
            effective_user: Telegram User object for profile extraction

        Returns:
            Tuple of (User instance or None on error, was_created)

        Requirements addressed:
            - 1.1: Create user record with telegram_id and profile data
            - 1.2: Set email to null and is_authenticated to false for new users
            - 1.3: Retrieve existing record instead of creating duplicate
            - 2.1: Set first_interaction_at to current UTC timestamp
            - 3.1: Set last_interaction_at to current UTC timestamp
        """
        try:
            with get_db_session() as session:
                # Query for existing user by telegram_id (Requirement 1.3)
                user = session.query(User).filter_by(telegram_id=telegram_id).first()

                if user:
                    # Existing user found - return without modification
                    logger.debug(f"Found existing user for {mask_telegram_id(telegram_id)}")
                    return user, False

                # New user - create with required fields
                current_time = datetime.now(UTC)

                # Extract profile data using existing utility (Requirement 1.1)
                profile_data = extract_user_profile(effective_user)

                # Create new user with:
                # - email=null, is_authenticated=false (Requirement 1.2)
                # - first_interaction_at and last_interaction_at set to current UTC time
                #   (Requirements 2.1, 3.1)
                user = User(
                    telegram_id=telegram_id,
                    email=None,  # Requirement 1.2: null for unauthenticated users
                    email_original=None,
                    is_authenticated=False,  # Requirement 1.2
                    created_at=current_time,
                    updated_at=current_time,
                    first_interaction_at=current_time,  # Requirement 2.1
                    last_interaction_at=current_time,  # Requirement 3.1
                    # Profile fields from Telegram (Requirement 1.1)
                    first_name=profile_data.get("first_name"),
                    last_name=profile_data.get("last_name"),
                    is_bot=profile_data.get("is_bot", False),
                    is_premium=profile_data.get("is_premium"),
                    language_code=profile_data.get("language_code"),
                )

                session.add(user)
                session.commit()

                logger.info(
                    f"Created new user for {mask_telegram_id(telegram_id)} "
                    f"with first_interaction_at={current_time.isoformat()}"
                )
                return user, True

        except IntegrityError as e:
            # Handle race condition where user was created between check and insert
            logger.warning(
                f"IntegrityError creating user for {mask_telegram_id(telegram_id)}: {e}. "
                "Attempting to retrieve existing user."
            )
            try:
                with get_db_session() as session:
                    user = session.query(User).filter_by(telegram_id=telegram_id).first()
                    if user:
                        return user, False
            except Exception as retry_error:
                logger.error(
                    f"Failed to retrieve user after IntegrityError for "
                    f"{mask_telegram_id(telegram_id)}: {retry_error}"
                )
            return None, False

        except Exception as e:
            logger.error(f"Error in get_or_create_user for {mask_telegram_id(telegram_id)}: {e}")
            return None, False

    def track_user_interaction(
        self,
        telegram_id: int,
        effective_user: Any | None,
    ) -> tuple[User | None, bool]:
        """
        Track a user interaction, creating or updating the user record.

        This method:
        1. Gets or creates the user record
        2. Updates last_interaction_at for existing users
        3. Checks if profile update is needed using should_update_user_profile
        4. Updates profile data if changes detected

        Args:
            telegram_id: User's Telegram ID
            effective_user: Telegram User object for profile extraction

        Returns:
            Tuple of (User instance or None on error, is_first_time_user)

        Requirements addressed:
            - 3.2: Update last_interaction_at on each interaction
            - 7.1: Track user interaction on any message or command
            - 7.2: Use UTC timezone for consistency
            - 7.3: Handle database errors gracefully
            - 7.4: Use should_update_user_profile to avoid unnecessary writes
        """
        try:
            # Step 1: Get or create user
            user, was_created = self.get_or_create_user(telegram_id, effective_user)

            if user is None:
                # get_or_create_user failed - graceful degradation (Requirement 7.3)
                logger.warning(
                    f"Failed to get or create user for {mask_telegram_id(telegram_id)}, "
                    "continuing with graceful degradation"
                )
                return None, False

            # For new users, they are first-time users by definition
            # (first_interaction_at == last_interaction_at from creation)
            if was_created:
                logger.debug(
                    f"New user created for {mask_telegram_id(telegram_id)}, is_first_time_user=True"
                )
                return user, True

            # Step 2 & 3 & 4: For existing users, update last_interaction_at and
            # check for profile updates
            try:
                with get_db_session() as session:
                    # Re-fetch user within this session to ensure we can update
                    db_user = session.query(User).filter_by(telegram_id=telegram_id).first()

                    if db_user is None:
                        # User was deleted between get_or_create and now - rare edge case
                        logger.warning(
                            f"User {mask_telegram_id(telegram_id)} not found during update"
                        )
                        return None, False

                    # Determine if this is a first-time user before updating
                    # (first_interaction_at == last_interaction_at means first time)
                    is_first_time = db_user.first_interaction_at == db_user.last_interaction_at

                    # Step 2: Update last_interaction_at to current UTC time (Requirement 3.2, 7.2)
                    current_time = datetime.now(UTC)
                    old_last_interaction = db_user.last_interaction_at
                    db_user.last_interaction_at = current_time

                    # Step 3 & 4: Check if profile update needed (Requirement 7.4)
                    if should_update_user_profile(db_user, effective_user):
                        profile_data = extract_user_profile(effective_user)
                        db_user.first_name = profile_data.get("first_name")
                        db_user.last_name = profile_data.get("last_name")
                        db_user.is_bot = profile_data.get("is_bot", False)
                        db_user.is_premium = profile_data.get("is_premium")
                        db_user.language_code = profile_data.get("language_code")
                        logger.debug(
                            f"Updated profile data for user {mask_telegram_id(telegram_id)}"
                        )

                    session.commit()

                    logger.debug(
                        f"Updated last_interaction_at for {mask_telegram_id(telegram_id)} "
                        f"from {old_last_interaction} to {current_time.isoformat()}, "
                        f"is_first_time_user={is_first_time}"
                    )

                    return db_user, is_first_time

            except Exception:
                # Database error during update - graceful degradation (Requirement 7.3)
                logger.exception(
                    f"Failed to update user interaction for {mask_telegram_id(telegram_id)}"
                )
                # Return the original user from get_or_create, even if update failed
                # This allows the bot to continue processing the request
                return user, False

        except Exception:
            # Catch-all for any unexpected errors - graceful degradation (Requirement 7.3)
            logger.exception(
                f"Unexpected error in track_user_interaction for {mask_telegram_id(telegram_id)}"
            )
            return None, False

    def is_first_time_user(self, user: User) -> bool:
        """
        Check if user is interacting for the first time.

        A user is considered a first-time user if their first_interaction_at
        timestamp equals their last_interaction_at timestamp.

        Args:
            user: User model instance

        Returns:
            True if first_interaction_at equals last_interaction_at, False otherwise

        Requirements addressed:
            - 4.1: Identify first-time user by equal timestamps
            - 4.2: Identify returning user by different timestamps
            - 4.3: Provide method to check if user is first-time
        """
        return user.first_interaction_at == user.last_interaction_at


# Global user tracking service instance
_user_tracking_service: UserTrackingService | None = None


def init_user_tracking_service() -> UserTrackingService:
    """
    Initialize global user tracking service.

    Returns:
        UserTrackingService instance
    """
    global _user_tracking_service
    _user_tracking_service = UserTrackingService()
    logger.info("User tracking service initialized")
    return _user_tracking_service


def get_user_tracking_service() -> UserTrackingService:
    """
    Get the global user tracking service instance.

    Returns:
        UserTrackingService instance

    Raises:
        RuntimeError: If user tracking service is not initialized
    """
    if _user_tracking_service is None:
        raise RuntimeError(
            "User tracking service not initialized. Call init_user_tracking_service() first."
        )
    return _user_tracking_service
