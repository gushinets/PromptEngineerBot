"""
Authentication service with OTP functionality.

This module provides core authentication logic including OTP generation,
verification, comprehensive rate limiting, and audit logging for all
authentication events.
"""

import logging
import re
import secrets
import time
from datetime import datetime, timezone
from typing import Optional, Tuple

from argon2 import PasswordHasher
from argon2.exceptions import HashingError, VerificationError
from sqlalchemy.exc import IntegrityError

from telegram_bot.auth.user_profile_utils import (
    extract_user_profile,
    should_update_user_profile,
)
from telegram_bot.data.database import (
    AuthEvent,
    User,
    get_db_session,
    mask_email,
    mask_telegram_id,
    normalize_email,
)
from telegram_bot.services.redis_client import get_redis_client
from telegram_bot.utils.config import BotConfig

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service for OTP generation, verification, and rate limiting."""

    def __init__(self, config: BotConfig):
        """
        Initialize authentication service.

        Args:
            config: Bot configuration with authentication settings
        """
        self.config = config
        self.redis_client = get_redis_client()
        self.password_hasher = PasswordHasher()

    def validate_email_format(self, email: str) -> bool:
        """
        Validate email format using basic regex validation.

        Args:
            email: Email address to validate

        Returns:
            True if email format is valid, False otherwise
        """
        if not email:
            return False

        # Check for consecutive dots (not allowed)
        if ".." in email:
            return False

        # Check for email injection attempts - more comprehensive
        injection_chars = ["\n", "\r", "\t", "\x0a", "\x0d", "%0a", "%0d"]
        if any(char in email for char in injection_chars):
            return False

        # Check for header injection patterns
        injection_patterns = [
            r"bcc\s*:",
            r"cc\s*:",
            r"to\s*:",
            r"subject\s*:",
            r"from\s*:",
            r"reply-to\s*:",
        ]
        email_lower = email.lower()
        if any(re.search(pattern, email_lower) for pattern in injection_patterns):
            return False

        # Basic email regex pattern
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    def generate_otp(self) -> str:
        """
        Generate a 6-digit numeric OTP.

        Returns:
            6-digit numeric OTP as string
        """
        # Generate cryptographically secure 6-digit OTP (100000-999999)
        otp = secrets.randbelow(900000) + 100000
        return str(otp)

    def hash_otp(self, otp: str) -> str:
        """
        Hash OTP using Argon2id with proper salt handling.

        Args:
            otp: Plain text OTP to hash

        Returns:
            Hashed OTP string

        Raises:
            HashingError: If hashing fails
        """
        try:
            return self.password_hasher.hash(otp)
        except HashingError as e:
            logger.error(f"Failed to hash OTP: {e}")
            raise

    def verify_otp_hash(self, otp: str, otp_hash: str) -> bool:
        """
        Verify OTP against stored hash.

        Args:
            otp: Plain text OTP to verify
            otp_hash: Stored OTP hash

        Returns:
            True if OTP matches hash, False otherwise
        """
        try:
            self.password_hasher.verify(otp_hash, otp)
            return True
        except VerificationError:
            return False
        except Exception as e:
            logger.error(f"Error verifying OTP hash: {e}")
            return False

    def check_rate_limits(self, telegram_id: int, email: str) -> Tuple[bool, str]:
        """
        Check all rate limiting rules comprehensively.

        Args:
            telegram_id: User's Telegram ID
            email: Normalized email address

        Returns:
            Tuple of (is_allowed, reason_if_blocked)
        """
        try:
            # Check email-based rate limiting (3/hour per normalized email)
            email_allowed, email_count = self.redis_client.check_email_rate_limit(
                email, self.config.email_rate_limit_per_hour
            )
            if not email_allowed:
                reason = f"email_limit_exceeded_{email_count}/{self.config.email_rate_limit_per_hour}"
                logger.warning(
                    f"Email rate limit exceeded for {mask_email(email)}: {email_count}/{self.config.email_rate_limit_per_hour}"
                )
                return False, reason

            # Check user-based rate limiting (5/hour per telegram_id)
            user_allowed, user_count = self.redis_client.check_user_rate_limit(
                telegram_id, self.config.user_rate_limit_per_hour
            )
            if not user_allowed:
                reason = f"user_limit_exceeded_{user_count}/{self.config.user_rate_limit_per_hour}"
                logger.warning(
                    f"User rate limit exceeded for {mask_telegram_id(telegram_id)}: {user_count}/{self.config.user_rate_limit_per_hour}"
                )
                return False, reason

            # Check spacing enforcement (60s minimum between sends)
            spacing_allowed, seconds_since_last = self.redis_client.check_spacing_limit(
                telegram_id, self.config.otp_spacing_seconds
            )
            if not spacing_allowed:
                remaining = self.config.otp_spacing_seconds - seconds_since_last
                reason = f"spacing_violation_{remaining}s_remaining"
                logger.warning(
                    f"Spacing violation for {mask_telegram_id(telegram_id)}: {seconds_since_last}s since last, need {self.config.otp_spacing_seconds}s"
                )
                return False, reason

            logger.debug(
                f"Rate limit check passed for {mask_telegram_id(telegram_id)}, {mask_email(email)}"
            )
            return True, ""

        except Exception as e:
            logger.error(f"Error checking rate limits: {e}")
            return False, "rate_check_error"

    def send_otp(
        self, telegram_id: int, email: str, email_original: Optional[str] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Generate and store OTP for user authentication.

        Args:
            telegram_id: User's Telegram ID
            email: Email address (will be normalized)
            email_original: Original email as entered by user (optional)

        Returns:
            Tuple of (success, message, otp_if_successful)
        """
        try:
            # Validate email format first
            if not self.validate_email_format(email):
                return False, "invalid_email_format", None

            # Normalize email and use original if provided
            normalized_email = normalize_email(email)
            original_email = email_original if email_original else email

            # Check comprehensive rate limits
            rate_allowed, rate_reason = self.check_rate_limits(
                telegram_id, normalized_email
            )
            if not rate_allowed:
                # Log rate limiting event
                self._log_auth_event(
                    telegram_id,
                    normalized_email,
                    "OTP_RATE_LIMITED",
                    False,
                    rate_reason,
                )
                return False, f"rate_limited_{rate_reason}", None

            # Generate and hash OTP
            otp = self.generate_otp()
            otp_hash = self.hash_otp(otp)

            # Store complete OTP context in Redis with 5-minute TTL
            success = self.redis_client.store_otp_with_original(
                telegram_id,
                otp_hash,
                normalized_email,
                original_email,
                self.config.otp_ttl_seconds,
            )

            if not success:
                logger.error(
                    f"Failed to store OTP in Redis for {mask_telegram_id(telegram_id)}"
                )
                self._log_auth_event(
                    telegram_id,
                    normalized_email,
                    "OTP_STORAGE_FAILED",
                    False,
                    "redis_error",
                )
                return False, "storage_failed", None

            # Increment rate limiting counters
            self.redis_client.increment_rate_limits(telegram_id, normalized_email)

            # Log successful OTP generation
            self._log_auth_event(telegram_id, normalized_email, "OTP_SENT", True, None)

            logger.info(
                f"OTP generated and stored for {mask_telegram_id(telegram_id)}, {mask_email(normalized_email)}"
            )

            # Return OTP for email service to send
            return True, "otp_sent", otp

        except Exception as e:
            logger.error(f"Error sending OTP: {e}")
            self._log_auth_event(
                telegram_id, email, "OTP_GENERATION_ERROR", False, str(e)
            )
            return False, "generation_error", None

    def verify_otp(
        self, telegram_id: int, otp: str, effective_user=None
    ) -> Tuple[bool, str]:
        """
        Verify OTP with attempt counting and comprehensive error handling.

        Args:
            telegram_id: User's Telegram ID
            otp: OTP to verify
            effective_user: Telegram User object for profile data extraction

        Returns:
            Tuple of (success, error_reason_if_failed)
        """
        try:
            # Get OTP data from Redis
            otp_data = self.redis_client.get_otp_data(telegram_id)
            if not otp_data:
                logger.warning(f"No OTP found for {mask_telegram_id(telegram_id)}")
                self._log_auth_event(
                    telegram_id, None, "OTP_NOT_FOUND", False, "no_otp_stored"
                )
                return False, "otp_not_found_or_expired"

            # Check if OTP has expired
            if otp_data.get("expires_at", 0) < time.time():
                logger.warning(f"OTP expired for {mask_telegram_id(telegram_id)}")
                self.redis_client.delete_otp(telegram_id, "expired")
                self._log_auth_event(
                    telegram_id,
                    otp_data.get("normalized_email"),
                    "OTP_EXPIRED",
                    False,
                    "expired",
                )
                return False, "otp_expired"

            # Increment attempt counter
            attempts = self.redis_client.increment_otp_attempts(telegram_id)
            if attempts == -1:
                logger.error(
                    f"Failed to increment attempts for {mask_telegram_id(telegram_id)}"
                )
                return False, "attempt_error"

            # Check if attempt limit exceeded (>3 attempts)
            if attempts > self.config.otp_max_attempts:
                logger.warning(
                    f"OTP attempt limit exceeded for {mask_telegram_id(telegram_id)}: {attempts}/{self.config.otp_max_attempts}"
                )
                self.redis_client.delete_otp(telegram_id, "attempt_limit_exceeded")
                self._log_auth_event(
                    telegram_id,
                    otp_data.get("normalized_email"),
                    "OTP_FAILED",
                    False,
                    "attempt_limit",
                )
                return False, "attempt_limit_exceeded"

            # Verify OTP hash
            otp_hash = otp_data.get("otp_hash")
            if not otp_hash:
                logger.error(f"No OTP hash found for {mask_telegram_id(telegram_id)}")
                return False, "invalid_data"

            is_valid = self.verify_otp_hash(otp, otp_hash)

            if is_valid:
                # OTP verification successful
                email = otp_data.get("normalized_email")
                email_original = otp_data.get("email_original")

                # Clean up Redis OTP data
                self.redis_client.delete_otp(telegram_id, "verification_success")

                # Persist authentication state
                success = self._persist_authentication_state(
                    telegram_id, email, email_original, effective_user
                )
                if not success:
                    logger.error(
                        f"Failed to persist auth state for {mask_telegram_id(telegram_id)}"
                    )
                    return False, "persistence_failed"

                # Log successful verification
                self._log_auth_event(telegram_id, email, "OTP_VERIFIED", True, None)

                logger.info(
                    f"OTP verification successful for {mask_telegram_id(telegram_id)}"
                )
                return True, "verification_successful"

            else:
                # OTP verification failed - check if this is the 3rd attempt
                if attempts >= self.config.otp_max_attempts:
                    # Delete OTP after max attempts reached
                    self.redis_client.delete_otp(telegram_id, "attempt_limit_exceeded")
                    self._log_auth_event(
                        telegram_id,
                        otp_data.get("normalized_email"),
                        "OTP_FAILED",
                        False,
                        "attempt_limit_exceeded",
                    )
                    return False, "attempt_limit_exceeded"
                else:
                    # Still have attempts left
                    logger.warning(
                        f"OTP verification failed for {mask_telegram_id(telegram_id)}, attempt {attempts}/{self.config.otp_max_attempts}"
                    )
                    self._log_auth_event(
                        telegram_id,
                        otp_data.get("normalized_email"),
                        "OTP_MISMATCH",
                        False,
                        f"attempt_{attempts}",
                    )
                    return False, f"invalid_otp_attempt_{attempts}"

        except Exception as e:
            logger.error(f"Error verifying OTP: {e}")
            self._log_auth_event(
                telegram_id, None, "OTP_VERIFICATION_ERROR", False, str(e)
            )
            return False, "verification_error"

    def _persist_authentication_state(
        self, telegram_id: int, email: str, email_original: str, effective_user=None
    ) -> bool:
        """
        Persist authentication state on OTP success.

        Args:
            telegram_id: User's Telegram ID
            email: Normalized email address
            email_original: Original email as entered by user
            effective_user: Telegram User object for profile data extraction

        Returns:
            True if persisted successfully, False otherwise
        """
        try:
            with get_db_session() as session:
                # Try to find existing user
                user = session.query(User).filter_by(telegram_id=telegram_id).first()

                current_time = datetime.now(timezone.utc)

                if user:
                    # Existing user - update authentication timestamps
                    user.email = email  # Update normalized email
                    user.email_original = email_original  # Update original email
                    user.is_authenticated = True
                    user.last_authenticated_at = current_time
                    user.updated_at = current_time

                    # Set email_verified_at only if it's not already set (first success)
                    if user.email_verified_at is None:
                        user.email_verified_at = current_time

                    # Check if profile data should be updated for existing user
                    try:
                        if should_update_user_profile(user, effective_user):
                            # Extract new profile data
                            new_profile_data = extract_user_profile(effective_user)

                            # Update profile fields with new data
                            user.first_name = new_profile_data.get("first_name")
                            user.last_name = new_profile_data.get("last_name")
                            user.is_bot = new_profile_data.get("is_bot", False)
                            user.is_premium = new_profile_data.get("is_premium")
                            user.language_code = new_profile_data.get("language_code")

                            # updated_at is already set above, ensuring timestamp update
                            logger.debug(
                                f"Updated profile data for existing user {mask_telegram_id(telegram_id)}"
                            )
                        else:
                            logger.debug(
                                f"No profile update needed for existing user {mask_telegram_id(telegram_id)}"
                            )
                    except Exception as e:
                        logger.warning(
                            f"Failed to update profile data for existing user {mask_telegram_id(telegram_id)}: {e}. "
                            "Continuing with authentication without profile update."
                        )

                    logger.debug(
                        f"Updated existing user for {mask_telegram_id(telegram_id)}"
                    )

                else:
                    # New user - check for email conflicts first
                    existing_email_user = (
                        session.query(User).filter_by(email=email).first()
                    )
                    if (
                        existing_email_user
                        and existing_email_user.telegram_id != telegram_id
                    ):
                        logger.error(
                            f"Email conflict: {mask_email(email)} already exists for different user"
                        )
                        return False

                    # Extract profile data for new user
                    profile_data = {}
                    try:
                        profile_data = extract_user_profile(effective_user)
                        logger.debug(
                            f"Extracted profile data for new user {mask_telegram_id(telegram_id)}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to extract profile data for {mask_telegram_id(telegram_id)}: {e}. "
                            "Continuing with user creation without profile data."
                        )
                        # Use safe defaults if profile extraction fails
                        profile_data = {
                            "first_name": None,
                            "last_name": None,
                            "is_bot": False,
                            "is_premium": None,
                            "language_code": None,
                        }

                    # Create new user with all required fields including profile data
                    user = User(
                        telegram_id=telegram_id,
                        email=email,
                        email_original=email_original,
                        is_authenticated=True,
                        email_verified_at=current_time,  # First success
                        last_authenticated_at=current_time,
                        created_at=current_time,
                        updated_at=current_time,
                        # Profile fields from Telegram
                        first_name=profile_data.get("first_name"),
                        last_name=profile_data.get("last_name"),
                        is_bot=profile_data.get("is_bot", False),
                        is_premium=profile_data.get("is_premium"),
                        language_code=profile_data.get("language_code"),
                    )
                    session.add(user)
                    logger.debug(
                        f"Created new user with profile data for {mask_telegram_id(telegram_id)}"
                    )

                session.commit()
                return True

        except IntegrityError as e:
            logger.error(f"Database integrity error persisting auth state: {e}")
            return False
        except Exception as e:
            logger.error(f"Error persisting authentication state: {e}")
            return False

    def is_user_authenticated(self, telegram_id: int) -> bool:
        """
        Check if user is already authenticated.

        Args:
            telegram_id: User's Telegram ID

        Returns:
            True if user is authenticated, False otherwise
        """
        try:
            with get_db_session() as session:
                user = (
                    session.query(User)
                    .filter_by(telegram_id=telegram_id, is_authenticated=True)
                    .first()
                )
                return user is not None

        except Exception as e:
            logger.error(f"Error checking authentication status: {e}")
            return False

    def get_user_email(self, telegram_id: int) -> Optional[str]:
        """
        Get authenticated user's normalized email.

        Args:
            telegram_id: User's Telegram ID

        Returns:
            Normalized email if user is authenticated, None otherwise
        """
        try:
            with get_db_session() as session:
                user = (
                    session.query(User)
                    .filter_by(telegram_id=telegram_id, is_authenticated=True)
                    .first()
                )
                return user.email if user else None

        except Exception as e:
            logger.error(f"Error getting user email: {e}")
            return None

    def _log_auth_event(
        self,
        telegram_id: int,
        email: Optional[str],
        event_type: str,
        success: bool,
        reason: Optional[str],
    ) -> None:
        """
        Log authentication event to audit trail.

        Args:
            telegram_id: User's Telegram ID
            email: Email address (masked for logging)
            event_type: Type of authentication event
            success: Whether the event was successful
            reason: Optional reason for failure
        """
        try:
            with get_db_session() as session:
                auth_event = AuthEvent(
                    telegram_id=telegram_id,
                    email=mask_email(email) if email else None,  # Store masked email
                    event_type=event_type,
                    success=success,
                    reason=reason,
                    created_at=datetime.now(timezone.utc),
                )
                session.add(auth_event)
                session.commit()

                logger.debug(
                    f"Auth event logged: {event_type} for {mask_telegram_id(telegram_id)}, success={success}"
                )

        except Exception as e:
            logger.error(f"Failed to log auth event: {e}")
            # Don't raise exception - logging failure shouldn't break auth flow


# Global auth service instance
auth_service: Optional[AuthService] = None


def init_auth_service(config: BotConfig) -> AuthService:
    """
    Initialize global authentication service.

    Args:
        config: Bot configuration

    Returns:
        AuthService instance
    """
    global auth_service
    auth_service = AuthService(config)
    return auth_service


def get_auth_service() -> AuthService:
    """
    Get the global authentication service instance.

    Returns:
        AuthService instance

    Raises:
        RuntimeError: If auth service is not initialized
    """
    if auth_service is None:
        raise RuntimeError(
            "Auth service not initialized. Call init_auth_service() first."
        )
    return auth_service
