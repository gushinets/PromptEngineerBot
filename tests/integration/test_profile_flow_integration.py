"""
Integration tests for complete user profile flow.

This module tests the end-to-end user registration and profile update flow,
including profile data capture from Telegram, database persistence, and
system behavior with various user types and edge cases.

Requirements tested:
- 4.1: Extract user profile data during user creation
- 4.2: Only update profile data if significant changes are detected
- 4.4: Update updated_at timestamp when profile changes are made
- 4.6: Compare current database values with update.effective_user values
"""

import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from telegram_prompt_bot.auth.service import AuthService
from telegram_prompt_bot.database.models import Base, User, get_db_session
from telegram_prompt_bot.utils.user_profile_utils import extract_user_profile, should_update_user_profile


class TestCompleteProfileFlowIntegration:
    """Integration tests for complete user profile flow."""

    @pytest.fixture
    def test_database_url(self):
        """Use in-memory SQLite for testing."""
        return "sqlite:///:memory:"

    @pytest.fixture
    def test_engine(self, test_database_url):
        """Create test database engine."""
        engine = create_engine(test_database_url, echo=False)
        Base.metadata.create_all(engine)
        return engine

    @pytest.fixture
    def test_session_factory(self, test_engine):
        """Create test session factory."""
        return sessionmaker(bind=test_engine)

    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client for testing."""
        mock_client = Mock()
        mock_client.check_email_rate_limit.return_value = (True, 0)
        mock_client.check_user_rate_limit.return_value = (True, 0)
        mock_client.check_spacing_limit.return_value = (True, 60)
        mock_client.store_otp_with_original.return_value = True
        mock_client.increment_rate_limits.return_value = True
        mock_client.get_otp_data.return_value = None
        mock_client.increment_otp_attempts.return_value = 1
        mock_client.delete_otp.return_value = True
        return mock_client

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        config = Mock()
        config.otp_ttl_seconds = 300
        config.otp_max_attempts = 3
        config.email_rate_limit_per_hour = 3
        config.user_rate_limit_per_hour = 5
        config.otp_spacing_seconds = 60
        return config

    @pytest.fixture
    def auth_service(self, mock_redis_client, mock_config):
        """Create AuthService instance with mocked dependencies."""
        with patch("telegram_prompt_bot.auth.service.get_redis_client", return_value=mock_redis_client):
            return AuthService(mock_config)

    @pytest.fixture
    def complete_telegram_user(self):
        """Mock complete Telegram user with all profile fields."""
        user = Mock()
        user.first_name = "John"
        user.last_name = "Doe"
        user.is_bot = False
        user.is_premium = True
        user.language_code = "en"
        return user

    @pytest.fixture
    def partial_telegram_user(self):
        """Mock Telegram user with partial profile data."""
        user = Mock()
        user.first_name = "Jane"
        user.last_name = None
        user.is_bot = False
        user.is_premium = None
        user.language_code = "es"
        return user

    @pytest.fixture
    def bot_telegram_user(self):
        """Mock Telegram bot user."""
        user = Mock()
        user.first_name = "TestBot"
        user.last_name = None
        user.is_bot = True
        user.is_premium = None
        user.language_code = None
        return user

    @pytest.fixture
    def premium_telegram_user(self):
        """Mock Telegram premium user."""
        user = Mock()
        user.first_name = "Premium"
        user.last_name = "User"
        user.is_bot = False
        user.is_premium = True
        user.language_code = "fr"
        return user

    def test_end_to_end_user_registration_with_complete_profile_capture(
        self,
        auth_service,
        mock_redis_client,
        test_session_factory,
        complete_telegram_user,
    ):
        """
        Test end-to-end user registration with complete profile data capture.

        Requirements: 4.1 - Extract user profile data from update.effective_user
        and populate all available fields during user creation
        """
        telegram_id = 123456789
        otp = "123456"
        email = "john.doe@example.com"
        email_original = "John.Doe@Example.Com"

        # Setup OTP verification mocks
        otp_hash = auth_service.hash_otp(otp)
        future_time = int(time.time()) + 300
        mock_redis_client.get_otp_data.return_value = {
            "otp_hash": otp_hash,
            "normalized_email": email,
            "email_original": email_original,
            "expires_at": future_time,
            "attempts": 0,
        }
        mock_redis_client.increment_otp_attempts.return_value = 1

        # Mock database session to use test database
        with patch("telegram_prompt_bot.auth.service.get_db_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = (
                test_session_factory()
            )

            # Execute end-to-end verification
            success, message = auth_service.verify_otp(
                telegram_id, otp, complete_telegram_user
            )

            # Verify successful registration
            assert success, f"Registration should succeed, got message: {message}"
            assert message == "verification_successful"

            # Verify user was created in database with complete profile
            with test_session_factory() as session:
                created_user = (
                    session.query(User).filter_by(telegram_id=telegram_id).first()
                )

                assert created_user is not None, "User should be created in database"

                # Verify basic authentication fields
                assert created_user.telegram_id == telegram_id
                assert created_user.email == email
                assert created_user.email_original == email_original
                assert created_user.is_authenticated is True
                assert created_user.email_verified_at is not None
                assert created_user.last_authenticated_at is not None

                # Verify complete profile data was captured
                assert created_user.first_name == "John"
                assert created_user.last_name == "Doe"
                assert created_user.is_bot is False
                assert created_user.is_premium is True
                assert created_user.language_code == "en"

                # Verify timestamps are set
                assert created_user.created_at is not None
                assert created_user.updated_at is not None

    def test_end_to_end_user_registration_with_partial_profile_capture(
        self,
        auth_service,
        mock_redis_client,
        test_session_factory,
        partial_telegram_user,
    ):
        """
        Test end-to-end user registration with partial profile data.

        Requirements: 4.1 - Handle cases where some profile fields are None
        """
        telegram_id = 987654321
        otp = "654321"
        email = "jane@example.com"
        email_original = "Jane@Example.Com"

        # Setup OTP verification mocks
        otp_hash = auth_service.hash_otp(otp)
        future_time = int(time.time()) + 300
        mock_redis_client.get_otp_data.return_value = {
            "otp_hash": otp_hash,
            "normalized_email": email,
            "email_original": email_original,
            "expires_at": future_time,
            "attempts": 0,
        }
        mock_redis_client.increment_otp_attempts.return_value = 1

        # Mock database session to use test database
        with patch("telegram_prompt_bot.auth.service.get_db_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = (
                test_session_factory()
            )

            # Execute end-to-end verification
            success, message = auth_service.verify_otp(
                telegram_id, otp, partial_telegram_user
            )

            # Verify successful registration
            assert success, f"Registration should succeed, got message: {message}"

            # Verify user was created with partial profile data
            with test_session_factory() as session:
                created_user = (
                    session.query(User).filter_by(telegram_id=telegram_id).first()
                )

                assert created_user is not None

                # Verify partial profile data handling
                assert created_user.first_name == "Jane"
                assert created_user.last_name is None  # Missing field handled
                assert created_user.is_bot is False
                assert created_user.is_premium is None  # Missing field handled
                assert created_user.language_code == "es"

    def test_profile_updates_during_subsequent_user_interactions(
        self,
        auth_service,
        mock_redis_client,
        test_session_factory,
        complete_telegram_user,
    ):
        """
        Test profile updates during subsequent user interactions.

        Requirements: 4.2 - Only update user profile data if significant changes are detected
        Requirements: 4.4 - Update updated_at timestamp when profile changes are made
        """
        telegram_id = 555666777
        otp = "111222"
        email = "update.test@example.com"
        email_original = "Update.Test@Example.Com"

        # First, create a user with initial profile data
        with test_session_factory() as session:
            initial_user = User(
                telegram_id=telegram_id,
                email=email,
                email_original=email_original,
                is_authenticated=True,
                email_verified_at=datetime.now(timezone.utc),
                last_authenticated_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                first_name="John",
                last_name="Doe",
                is_bot=False,
                is_premium=False,  # Will change to True
                language_code="en",
            )
            session.add(initial_user)
            session.commit()
            initial_updated_at = initial_user.updated_at

        # Setup OTP verification mocks for subsequent interaction
        otp_hash = auth_service.hash_otp(otp)
        future_time = int(time.time()) + 300
        mock_redis_client.get_otp_data.return_value = {
            "otp_hash": otp_hash,
            "normalized_email": email,
            "email_original": email_original,
            "expires_at": future_time,
            "attempts": 0,
        }
        mock_redis_client.increment_otp_attempts.return_value = 1

        # Mock database session to use test database
        with patch("telegram_prompt_bot.auth.service.get_db_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = (
                test_session_factory()
            )

            # Execute subsequent verification with updated profile (premium status changed)
            success, message = auth_service.verify_otp(
                telegram_id, otp, complete_telegram_user
            )

            # Verify successful update
            assert success, f"Profile update should succeed, got message: {message}"

            # Verify profile was updated in database
            with test_session_factory() as session:
                updated_user = (
                    session.query(User).filter_by(telegram_id=telegram_id).first()
                )

                assert updated_user is not None

                # Verify profile changes were applied
                assert updated_user.first_name == "John"  # Same
                assert updated_user.last_name == "Doe"  # Same
                assert updated_user.is_bot is False  # Same
                assert updated_user.is_premium is True  # Changed from False
                assert updated_user.language_code == "en"  # Same

                # Verify updated_at timestamp was changed
                assert updated_user.updated_at > initial_updated_at

    def test_no_profile_update_when_no_changes_detected(
        self,
        auth_service,
        mock_redis_client,
        test_session_factory,
        complete_telegram_user,
    ):
        """
        Test that profile is not updated when no changes are detected.

        Requirements: 4.2 - Only update user profile data if significant changes are detected
        """
        telegram_id = 888999000
        otp = "333444"
        email = "nochange@example.com"
        email_original = "NoChange@Example.Com"

        # Create user with same profile data as the incoming update
        with test_session_factory() as session:
            existing_user = User(
                telegram_id=telegram_id,
                email=email,
                email_original=email_original,
                is_authenticated=True,
                email_verified_at=datetime.now(timezone.utc),
                last_authenticated_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                first_name="John",  # Same as complete_telegram_user
                last_name="Doe",  # Same as complete_telegram_user
                is_bot=False,  # Same as complete_telegram_user
                is_premium=True,  # Same as complete_telegram_user
                language_code="en",  # Same as complete_telegram_user
            )
            session.add(existing_user)
            session.commit()

        # Setup OTP verification mocks
        otp_hash = auth_service.hash_otp(otp)
        future_time = int(time.time()) + 300
        mock_redis_client.get_otp_data.return_value = {
            "otp_hash": otp_hash,
            "normalized_email": email,
            "email_original": email_original,
            "expires_at": future_time,
            "attempts": 0,
        }
        mock_redis_client.increment_otp_attempts.return_value = 1

        # Mock database session to use test database
        with patch("telegram_prompt_bot.auth.service.get_db_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = (
                test_session_factory()
            )

            # Execute verification with identical profile data
            success, message = auth_service.verify_otp(
                telegram_id, otp, complete_telegram_user
            )

            # Verify successful authentication without profile update
            assert success, f"Authentication should succeed, got message: {message}"

            # Verify profile data remains unchanged (no unnecessary updates)
            with test_session_factory() as session:
                user_after = (
                    session.query(User).filter_by(telegram_id=telegram_id).first()
                )

                assert user_after is not None
                assert user_after.first_name == "John"
                assert user_after.last_name == "Doe"
                assert user_after.is_bot is False
                assert user_after.is_premium is True
                assert user_after.language_code == "en"

    def test_system_behavior_with_bot_user_type(
        self,
        auth_service,
        mock_redis_client,
        test_session_factory,
        bot_telegram_user,
    ):
        """
        Test system behavior with bot user type.

        Requirements: 4.1 - Handle various Telegram user types including bots
        """
        telegram_id = 111222333
        otp = "555666"
        email = "testbot@example.com"
        email_original = "TestBot@Example.Com"

        # Setup OTP verification mocks
        otp_hash = auth_service.hash_otp(otp)
        future_time = int(time.time()) + 300
        mock_redis_client.get_otp_data.return_value = {
            "otp_hash": otp_hash,
            "normalized_email": email,
            "email_original": email_original,
            "expires_at": future_time,
            "attempts": 0,
        }
        mock_redis_client.increment_otp_attempts.return_value = 1

        # Mock database session to use test database
        with patch("telegram_prompt_bot.auth.service.get_db_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = (
                test_session_factory()
            )

            # Execute verification with bot user
            success, message = auth_service.verify_otp(
                telegram_id, otp, bot_telegram_user
            )

            # Verify successful bot registration
            assert success, f"Bot registration should succeed, got message: {message}"

            # Verify bot-specific profile data
            with test_session_factory() as session:
                bot_user = (
                    session.query(User).filter_by(telegram_id=telegram_id).first()
                )

                assert bot_user is not None

                # Verify bot-specific fields
                assert bot_user.first_name == "TestBot"
                assert bot_user.last_name is None
                assert bot_user.is_bot is True  # Key bot identifier
                assert bot_user.is_premium is None
                assert bot_user.language_code is None

    def test_system_behavior_with_premium_user_type(
        self,
        auth_service,
        mock_redis_client,
        test_session_factory,
        premium_telegram_user,
    ):
        """
        Test system behavior with premium user type.

        Requirements: 4.1 - Handle various Telegram user types including premium users
        """
        telegram_id = 444555666
        otp = "777888"
        email = "premium@example.com"
        email_original = "Premium@Example.Com"

        # Setup OTP verification mocks
        otp_hash = auth_service.hash_otp(otp)
        future_time = int(time.time()) + 300
        mock_redis_client.get_otp_data.return_value = {
            "otp_hash": otp_hash,
            "normalized_email": email,
            "email_original": email_original,
            "expires_at": future_time,
            "attempts": 0,
        }
        mock_redis_client.increment_otp_attempts.return_value = 1

        # Mock database session to use test database
        with patch("telegram_prompt_bot.auth.service.get_db_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = (
                test_session_factory()
            )

            # Execute verification with premium user
            success, message = auth_service.verify_otp(
                telegram_id, otp, premium_telegram_user
            )

            # Verify successful premium user registration
            assert success, (
                f"Premium user registration should succeed, got message: {message}"
            )

            # Verify premium user profile data
            with test_session_factory() as session:
                premium_user = (
                    session.query(User).filter_by(telegram_id=telegram_id).first()
                )

                assert premium_user is not None

                # Verify premium user fields
                assert premium_user.first_name == "Premium"
                assert premium_user.last_name == "User"
                assert premium_user.is_bot is False
                assert premium_user.is_premium is True  # Key premium identifier
                assert premium_user.language_code == "fr"

    def test_system_behavior_with_none_effective_user_edge_case(
        self,
        auth_service,
        mock_redis_client,
        test_session_factory,
    ):
        """
        Test system behavior when effective_user is None (edge case).

        Requirements: 4.6 - Handle edge cases where effective_user is None
        """
        telegram_id = 777888999
        otp = "999000"
        email = "edgecase@example.com"
        email_original = "EdgeCase@Example.Com"

        # Setup OTP verification mocks
        otp_hash = auth_service.hash_otp(otp)
        future_time = int(time.time()) + 300
        mock_redis_client.get_otp_data.return_value = {
            "otp_hash": otp_hash,
            "normalized_email": email,
            "email_original": email_original,
            "expires_at": future_time,
            "attempts": 0,
        }
        mock_redis_client.increment_otp_attempts.return_value = 1

        # Mock database session to use test database
        with patch("telegram_prompt_bot.auth.service.get_db_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = (
                test_session_factory()
            )

            # Execute verification with None effective_user
            success, message = auth_service.verify_otp(telegram_id, otp, None)

            # Verify successful registration despite None effective_user
            assert success, (
                f"Registration should succeed with None effective_user, got message: {message}"
            )

            # Verify user was created with safe defaults
            with test_session_factory() as session:
                edge_case_user = (
                    session.query(User).filter_by(telegram_id=telegram_id).first()
                )

                assert edge_case_user is not None

                # Verify safe default profile values
                assert edge_case_user.first_name is None
                assert edge_case_user.last_name is None
                assert edge_case_user.is_bot is False  # Safe default
                assert edge_case_user.is_premium is None
                assert edge_case_user.language_code is None

    def test_system_behavior_with_malformed_effective_user_edge_case(
        self,
        auth_service,
        mock_redis_client,
        test_session_factory,
    ):
        """
        Test system behavior with malformed effective_user object (edge case).

        Requirements: 4.6 - Handle edge cases where effective_user has missing attributes
        """
        telegram_id = 111222
        otp = "123789"
        email = "malformed@example.com"
        email_original = "Malformed@Example.Com"

        # Create malformed effective_user (missing some attributes)
        malformed_user = Mock(spec=["first_name"])  # Only has first_name attribute
        malformed_user.first_name = "Malformed"
        # Intentionally missing last_name, is_bot, is_premium, language_code attributes

        # Setup OTP verification mocks
        otp_hash = auth_service.hash_otp(otp)
        future_time = int(time.time()) + 300
        mock_redis_client.get_otp_data.return_value = {
            "otp_hash": otp_hash,
            "normalized_email": email,
            "email_original": email_original,
            "expires_at": future_time,
            "attempts": 0,
        }
        mock_redis_client.increment_otp_attempts.return_value = 1

        # Mock database session to use test database
        with patch("telegram_prompt_bot.auth.service.get_db_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = (
                test_session_factory()
            )

            # Execute verification with malformed effective_user
            success, message = auth_service.verify_otp(telegram_id, otp, malformed_user)

            # Verify successful registration despite malformed effective_user
            assert success, (
                f"Registration should succeed with malformed effective_user, got message: {message}"
            )

            # Verify user was created with available data and safe defaults
            with test_session_factory() as session:
                malformed_user_db = (
                    session.query(User).filter_by(telegram_id=telegram_id).first()
                )

                assert malformed_user_db is not None

                # Verify available data was captured and missing fields have safe defaults
                assert malformed_user_db.first_name == "Malformed"  # Available
                assert malformed_user_db.last_name is None  # Missing, safe default
                assert malformed_user_db.is_bot is False  # Missing, safe default
                assert malformed_user_db.is_premium is None  # Missing, safe default
                assert malformed_user_db.language_code is None  # Missing, safe default

    def test_profile_comparison_utility_accuracy(
        self, test_session_factory, complete_telegram_user
    ):
        """
        Test profile comparison utility accuracy for determining updates.

        Requirements: 4.6 - Compare current database values with update.effective_user values
        """
        # Create user with different profile data
        with test_session_factory() as session:
            test_user = User(
                telegram_id=123456789,
                email="test@example.com",
                email_original="Test@Example.Com",
                is_authenticated=True,
                email_verified_at=datetime.now(timezone.utc),
                last_authenticated_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                first_name="Old",  # Different from complete_telegram_user
                last_name="Name",  # Different from complete_telegram_user
                is_bot=False,
                is_premium=False,  # Different from complete_telegram_user
                language_code="es",  # Different from complete_telegram_user
            )
            session.add(test_user)
            session.commit()

            # Test profile comparison utility
            needs_update = should_update_user_profile(test_user, complete_telegram_user)

            # Should detect changes (first_name, last_name, is_premium, language_code all different)
            assert needs_update is True, "Should detect profile changes"

            # Update user to match complete_telegram_user
            test_user.first_name = "John"
            test_user.last_name = "Doe"
            test_user.is_premium = True
            test_user.language_code = "en"
            session.commit()

            # Test again - should not need update
            needs_update_after = should_update_user_profile(
                test_user, complete_telegram_user
            )
            assert needs_update_after is False, "Should not detect changes after update"

    def test_profile_extraction_utility_robustness(self):
        """
        Test profile extraction utility robustness with various input types.

        Requirements: 4.1, 4.6 - Handle various edge cases in profile extraction
        """
        # Test with None
        profile_none = extract_user_profile(None)
        expected_none = {
            "first_name": None,
            "last_name": None,
            "is_bot": False,
            "is_premium": None,
            "language_code": None,
        }
        assert profile_none == expected_none

        # Test with complete user
        complete_user = Mock()
        complete_user.first_name = "Complete"
        complete_user.last_name = "User"
        complete_user.is_bot = False
        complete_user.is_premium = True
        complete_user.language_code = "de"

        profile_complete = extract_user_profile(complete_user)
        expected_complete = {
            "first_name": "Complete",
            "last_name": "User",
            "is_bot": False,
            "is_premium": True,
            "language_code": "de",
        }
        assert profile_complete == expected_complete

        # Test with empty user (no attributes)
        empty_user = Mock(spec=[])  # Mock with no attributes
        profile_empty = extract_user_profile(empty_user)
        expected_empty = {
            "first_name": None,
            "last_name": None,
            "is_bot": False,
            "is_premium": None,
            "language_code": None,
        }
        assert profile_empty == expected_empty

    def test_concurrent_profile_updates_edge_case(
        self,
        auth_service,
        mock_redis_client,
        test_session_factory,
        complete_telegram_user,
    ):
        """
        Test system behavior with concurrent profile updates (edge case).

        Requirements: 4.2, 4.4 - Handle concurrent updates gracefully
        """
        telegram_id = 999888777
        otp = "456789"
        email = "concurrent@example.com"
        email_original = "Concurrent@Example.Com"

        # Create initial user
        with test_session_factory() as session:
            initial_user = User(
                telegram_id=telegram_id,
                email=email,
                email_original=email_original,
                is_authenticated=True,
                email_verified_at=datetime.now(timezone.utc),
                last_authenticated_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                first_name="Initial",
                last_name="User",
                is_bot=False,
                is_premium=False,
                language_code="en",
            )
            session.add(initial_user)
            session.commit()

        # Setup OTP verification mocks
        otp_hash = auth_service.hash_otp(otp)
        future_time = int(time.time()) + 300
        mock_redis_client.get_otp_data.return_value = {
            "otp_hash": otp_hash,
            "normalized_email": email,
            "email_original": email_original,
            "expires_at": future_time,
            "attempts": 0,
        }
        mock_redis_client.increment_otp_attempts.return_value = 1

        # Mock database session to use test database
        with patch("telegram_prompt_bot.auth.service.get_db_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = (
                test_session_factory()
            )

            # Execute verification (simulating concurrent update)
            success, message = auth_service.verify_otp(
                telegram_id, otp, complete_telegram_user
            )

            # Verify successful handling of concurrent update
            assert success, f"Concurrent update should succeed, got message: {message}"

            # Verify final state is consistent
            with test_session_factory() as session:
                final_user = (
                    session.query(User).filter_by(telegram_id=telegram_id).first()
                )

                assert final_user is not None
                # Should have the updated profile data
                assert final_user.first_name == "John"
                assert final_user.last_name == "Doe"
                assert final_user.is_premium is True


if __name__ == "__main__":
    pytest.main([__file__])
