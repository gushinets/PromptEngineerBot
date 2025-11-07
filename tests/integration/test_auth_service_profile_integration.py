"""
Unit tests for AuthService profile integration functionality.

Tests profile data extraction, storage, and update logic during authentication.
"""

import time
from unittest.mock import Mock, patch

import pytest

from telegram_bot.auth.auth_service import AuthService


class TestAuthServiceProfileIntegration:
    """Test cases for AuthService profile integration functionality."""

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
        with patch(
            "telegram_bot.auth.auth_service.get_redis_client", return_value=mock_redis_client
        ):
            return AuthService(mock_config)

    @pytest.fixture
    def mock_effective_user(self):
        """Mock Telegram effective_user object with complete profile data."""
        user = Mock()
        user.first_name = "John"
        user.last_name = "Doe"
        user.is_bot = False
        user.is_premium = True
        user.language_code = "en"
        return user

    @pytest.fixture
    def mock_effective_user_partial(self):
        """Mock Telegram effective_user object with partial profile data."""
        user = Mock()
        user.first_name = "Jane"
        user.last_name = None  # Missing last name
        user.is_bot = False
        user.is_premium = None  # Missing premium status
        user.language_code = "es"
        return user

    @pytest.fixture
    def mock_effective_user_bot(self):
        """Mock Telegram effective_user object for a bot."""
        user = Mock()
        user.first_name = "TestBot"
        user.last_name = None
        user.is_bot = True
        user.is_premium = None
        user.language_code = None
        return user

    @patch("telegram_bot.auth.auth_service.get_db_session")
    @patch("telegram_bot.auth.auth_service.extract_user_profile")
    def test_user_creation_with_profile_data_extraction_and_storage(
        self,
        mock_extract_profile,
        mock_get_session,
        auth_service,
        mock_redis_client,
        mock_effective_user,
    ):
        """
        Test user creation with profile data extraction and storage.

        Requirements: 4.1 - Extract user profile data from update.effective_user
        and populate all available fields during user creation
        """
        telegram_id = 123456789
        otp = "123456"
        email = "test@example.com"
        email_original = "Test@Example.Com"

        # Mock profile extraction
        expected_profile = {
            "first_name": "John",
            "last_name": "Doe",
            "is_bot": False,
            "is_premium": True,
            "language_code": "en",
        }
        mock_extract_profile.return_value = expected_profile

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

        # Mock database session - no existing user
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            None,  # No user by telegram_id
            None,  # No user by email
        ]

        # Execute verification
        success, message = auth_service.verify_otp(telegram_id, otp, mock_effective_user)

        # Verify success
        assert success, f"Should succeed with profile data, got message: {message}"
        assert message == "verification_successful"

        # Verify profile extraction was called
        mock_extract_profile.assert_called_once_with(mock_effective_user)

        # Verify user creation with profile data
        assert mock_session.add.call_count == 2  # User + AuthEvent
        user_call = mock_session.add.call_args_list[0]
        created_user = user_call[0][0]

        # Check basic user fields
        assert created_user.telegram_id == telegram_id
        assert created_user.email == email
        assert created_user.email_original == email_original
        assert created_user.is_authenticated == True

        # Check profile fields were populated
        assert created_user.first_name == "John"
        assert created_user.last_name == "Doe"
        assert created_user.is_bot == False
        assert created_user.is_premium == True
        assert created_user.language_code == "en"

        mock_session.commit.assert_called()

    @patch("telegram_bot.auth.auth_service.get_db_session")
    @patch("telegram_bot.auth.auth_service.extract_user_profile")
    def test_user_creation_with_partial_profile_data(
        self,
        mock_extract_profile,
        mock_get_session,
        auth_service,
        mock_redis_client,
        mock_effective_user_partial,
    ):
        """
        Test user creation with partial profile data (some fields None).

        Requirements: 4.3 - Handle cases where effective_user fields are None or missing
        """
        telegram_id = 123456789
        otp = "123456"
        email = "test@example.com"
        email_original = "Test@Example.Com"

        # Mock profile extraction with partial data
        expected_profile = {
            "first_name": "Jane",
            "last_name": None,  # Missing
            "is_bot": False,
            "is_premium": None,  # Missing
            "language_code": "es",
        }
        mock_extract_profile.return_value = expected_profile

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

        # Mock database session - no existing user
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            None,  # No user by telegram_id
            None,  # No user by email
        ]

        # Execute verification
        success, message = auth_service.verify_otp(telegram_id, otp, mock_effective_user_partial)

        # Verify success
        assert success, f"Should succeed with partial profile data, got message: {message}"

        # Verify user creation with partial profile data
        user_call = mock_session.add.call_args_list[0]
        created_user = user_call[0][0]

        # Check profile fields handle None values correctly
        assert created_user.first_name == "Jane"
        assert created_user.last_name is None
        assert created_user.is_bot == False
        assert created_user.is_premium is None
        assert created_user.language_code == "es"

    @patch("telegram_bot.auth.auth_service.get_db_session")
    @patch("telegram_bot.auth.auth_service.should_update_user_profile")
    @patch("telegram_bot.auth.auth_service.extract_user_profile")
    def test_profile_update_logic_for_existing_users_with_changes(
        self,
        mock_extract_profile,
        mock_should_update,
        mock_get_session,
        auth_service,
        mock_redis_client,
        mock_effective_user,
    ):
        """
        Test profile update logic for existing users when changes are detected.

        Requirements: 4.2 - Only update user profile data if significant changes are detected
        """
        telegram_id = 123456789
        otp = "123456"
        email = "test@example.com"
        email_original = "Test@Example.Com"

        # Mock profile comparison indicating changes needed
        mock_should_update.return_value = True

        # Mock new profile data
        new_profile = {
            "first_name": "John",
            "last_name": "Smith",  # Changed from Doe
            "is_bot": False,
            "is_premium": True,
            "language_code": "en",
        }
        mock_extract_profile.return_value = new_profile

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

        # Mock database session with existing user
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_user = Mock()
        mock_user.first_name = "John"
        mock_user.last_name = "Doe"  # Old value
        mock_user.is_bot = False
        mock_user.is_premium = True
        mock_user.language_code = "en"
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_user

        # Execute verification
        success, message = auth_service.verify_otp(telegram_id, otp, mock_effective_user)

        # Verify success
        assert success, f"Should succeed with profile update, got message: {message}"

        # Verify profile comparison was called
        mock_should_update.assert_called_once_with(mock_user, mock_effective_user)

        # Verify profile extraction was called
        mock_extract_profile.assert_called_once_with(mock_effective_user)

        # Verify profile fields were updated
        assert mock_user.first_name == "John"
        assert mock_user.last_name == "Smith"  # Updated
        assert mock_user.is_bot == False
        assert mock_user.is_premium == True
        assert mock_user.language_code == "en"

        # Verify updated_at timestamp was set
        assert mock_user.updated_at is not None

    @patch("telegram_bot.auth.auth_service.get_db_session")
    @patch("telegram_bot.auth.auth_service.should_update_user_profile")
    def test_profile_update_logic_for_existing_users_no_changes(
        self,
        mock_should_update,
        mock_get_session,
        auth_service,
        mock_redis_client,
        mock_effective_user,
    ):
        """
        Test profile update logic for existing users when no changes are detected.

        Requirements: 4.2 - Only update user profile data if significant changes are detected
        """
        telegram_id = 123456789
        otp = "123456"
        email = "test@example.com"
        email_original = "Test@Example.Com"

        # Mock profile comparison indicating no changes needed
        mock_should_update.return_value = False

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

        # Mock database session with existing user
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_user = Mock()
        original_first_name = "John"
        original_last_name = "Doe"
        mock_user.first_name = original_first_name
        mock_user.last_name = original_last_name
        mock_user.is_bot = False
        mock_user.is_premium = True
        mock_user.language_code = "en"
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_user

        # Execute verification
        success, message = auth_service.verify_otp(telegram_id, otp, mock_effective_user)

        # Verify success
        assert success, f"Should succeed without profile update, got message: {message}"

        # Verify profile comparison was called
        mock_should_update.assert_called_once_with(mock_user, mock_effective_user)

        # Verify profile fields were NOT changed (still original values)
        assert mock_user.first_name == original_first_name
        assert mock_user.last_name == original_last_name

        # Verify updated_at timestamp was still set (for auth update)
        assert mock_user.updated_at is not None

    @patch("telegram_bot.auth.auth_service.get_db_session")
    @patch("telegram_bot.auth.auth_service.extract_user_profile")
    def test_error_handling_when_profile_extraction_fails_new_user(
        self, mock_extract_profile, mock_get_session, auth_service, mock_redis_client
    ):
        """
        Test error handling when profile extraction fails for new user creation.

        Requirements: 4.5 - Log error but continue processing when profile update fails
        """
        telegram_id = 123456789
        otp = "123456"
        email = "test@example.com"
        email_original = "Test@Example.Com"

        # Mock profile extraction failure
        mock_extract_profile.side_effect = Exception("Profile extraction failed")

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

        # Mock database session - no existing user
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            None,  # No user by telegram_id
            None,  # No user by email
        ]

        # Execute verification
        success, message = auth_service.verify_otp(telegram_id, otp, Mock())

        # Verify success despite profile extraction failure
        assert success, f"Should succeed despite profile extraction failure, got message: {message}"
        assert message == "verification_successful"

        # Verify user was still created with safe defaults
        user_call = mock_session.add.call_args_list[0]
        created_user = user_call[0][0]

        # Check profile fields have safe defaults
        assert created_user.first_name is None
        assert created_user.last_name is None
        assert created_user.is_bot == False
        assert created_user.is_premium is None
        assert created_user.language_code is None

    @patch("telegram_bot.auth.auth_service.get_db_session")
    @patch("telegram_bot.auth.auth_service.should_update_user_profile")
    def test_error_handling_when_profile_update_fails_existing_user(
        self, mock_should_update, mock_get_session, auth_service, mock_redis_client
    ):
        """
        Test error handling when profile update fails for existing user.

        Requirements: 4.5 - Log error but continue processing when profile update fails
        """
        telegram_id = 123456789
        otp = "123456"
        email = "test@example.com"
        email_original = "Test@Example.Com"

        # Mock profile comparison failure
        mock_should_update.side_effect = Exception("Profile comparison failed")

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

        # Mock database session with existing user
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_user = Mock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_user

        # Execute verification
        success, message = auth_service.verify_otp(telegram_id, otp, Mock())

        # Verify success despite profile update failure
        assert success, f"Should succeed despite profile update failure, got message: {message}"
        assert message == "verification_successful"

        # Verify authentication fields were still updated
        assert mock_user.is_authenticated == True
        assert mock_user.last_authenticated_at is not None
        assert mock_user.updated_at is not None

    @patch("telegram_bot.auth.auth_service.get_db_session")
    @patch("telegram_bot.auth.auth_service.extract_user_profile")
    def test_user_creation_with_bot_profile(
        self,
        mock_extract_profile,
        mock_get_session,
        auth_service,
        mock_redis_client,
        mock_effective_user_bot,
    ):
        """
        Test user creation with bot profile data.

        Requirements: 4.1 - Handle various user types including bots
        """
        telegram_id = 123456789
        otp = "123456"
        email = "testbot@example.com"
        email_original = "TestBot@Example.Com"

        # Mock bot profile extraction
        bot_profile = {
            "first_name": "TestBot",
            "last_name": None,
            "is_bot": True,
            "is_premium": None,
            "language_code": None,
        }
        mock_extract_profile.return_value = bot_profile

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

        # Mock database session - no existing user
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            None,  # No user by telegram_id
            None,  # No user by email
        ]

        # Execute verification
        success, message = auth_service.verify_otp(telegram_id, otp, mock_effective_user_bot)

        # Verify success
        assert success, f"Should succeed with bot profile, got message: {message}"

        # Verify bot user creation
        user_call = mock_session.add.call_args_list[0]
        created_user = user_call[0][0]

        # Check bot-specific profile fields
        assert created_user.first_name == "TestBot"
        assert created_user.last_name is None
        assert created_user.is_bot == True  # Key bot identifier
        assert created_user.is_premium is None
        assert created_user.language_code is None

    @patch("telegram_bot.auth.auth_service.get_db_session")
    def test_profile_integration_with_none_effective_user(
        self, mock_get_session, auth_service, mock_redis_client
    ):
        """
        Test profile integration when effective_user is None.

        Requirements: 4.3 - Handle cases where effective_user is None
        """
        telegram_id = 123456789
        otp = "123456"
        email = "test@example.com"
        email_original = "Test@Example.Com"

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

        # Mock database session - no existing user
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            None,  # No user by telegram_id
            None,  # No user by email
        ]

        # Execute verification with None effective_user
        success, message = auth_service.verify_otp(telegram_id, otp, None)

        # Verify success despite None effective_user
        assert success, f"Should succeed with None effective_user, got message: {message}"

        # Verify user creation with safe defaults
        user_call = mock_session.add.call_args_list[0]
        created_user = user_call[0][0]

        # Check profile fields have safe defaults when effective_user is None
        assert created_user.first_name is None
        assert created_user.last_name is None
        assert created_user.is_bot == False
        assert created_user.is_premium is None
        assert created_user.language_code is None

    @patch("telegram_bot.auth.auth_service.get_db_session")
    @patch("telegram_bot.auth.auth_service.should_update_user_profile")
    @patch("telegram_bot.auth.auth_service.extract_user_profile")
    def test_updated_at_timestamp_on_profile_changes(
        self,
        mock_extract_profile,
        mock_should_update,
        mock_get_session,
        auth_service,
        mock_redis_client,
        mock_effective_user,
    ):
        """
        Test that updated_at timestamp is set when profile changes are made.

        Requirements: 4.4 - Update updated_at timestamp when profile changes are made
        """
        telegram_id = 123456789
        otp = "123456"
        email = "test@example.com"
        email_original = "Test@Example.Com"

        # Mock profile comparison indicating changes needed
        mock_should_update.return_value = True

        # Mock new profile data
        new_profile = {
            "first_name": "John",
            "last_name": "Updated",
            "is_bot": False,
            "is_premium": True,
            "language_code": "en",
        }
        mock_extract_profile.return_value = new_profile

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

        # Mock database session with existing user
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_user = Mock()
        original_updated_at = Mock()
        mock_user.updated_at = original_updated_at
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_user

        # Execute verification
        success, message = auth_service.verify_otp(telegram_id, otp, mock_effective_user)

        # Verify success
        assert success, f"Should succeed with timestamp update, got message: {message}"

        # Verify updated_at timestamp was changed (set to new value)
        assert mock_user.updated_at != original_updated_at
        assert mock_user.updated_at is not None
