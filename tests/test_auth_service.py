"""
Unit tests for authentication service.

Tests OTP generation, hashing, verification, rate limiting, and user persistence.
"""

import base64
import hashlib
import time
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.auth_service import AuthService, get_auth_service, init_auth_service
from src.database import User


class TestAuthService:
    """Test cases for AuthService class."""

    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client for testing."""
        mock_client = Mock()
        mock_client.check_email_rate_limit.return_value = (True, 0)
        mock_client.check_user_rate_limit.return_value = (True, 0)
        mock_client.check_spacing_limit.return_value = (True, 60)
        mock_client.store_otp.return_value = True
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
        with patch("src.auth_service.get_redis_client", return_value=mock_redis_client):
            return AuthService(mock_config)

    def test_validate_email_format_valid(self, auth_service):
        """Test email format validation with valid emails."""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            "123@test.com",
            "a@b.co",
        ]

        for email in valid_emails:
            assert auth_service.validate_email_format(email), (
                f"Should accept valid email: {email}"
            )

    def test_validate_email_format_invalid(self, auth_service):
        """Test email format validation with invalid emails."""
        invalid_emails = [
            "",
            "invalid",
            "@example.com",
            "user@",
            "user@domain",
            "user..name@example.com",
            "user@domain..com",
            None,
        ]

        for email in invalid_emails:
            assert not auth_service.validate_email_format(email), (
                f"Should reject invalid email: {email}"
            )

    def test_generate_otp(self, auth_service):
        """Test OTP generation creates 6-digit numeric code."""
        for _ in range(100):  # Test multiple generations
            otp = auth_service.generate_otp()

            # Should be exactly 6 digits
            assert len(otp) == 6, f"OTP should be 6 digits, got: {otp}"

            # Should be numeric
            assert otp.isdigit(), f"OTP should be numeric, got: {otp}"

            # Should be in valid range (100000-999999)
            otp_int = int(otp)
            assert 100000 <= otp_int <= 999999, (
                f"OTP should be 6 digits, got: {otp_int}"
            )

    def test_otp_hashing(self, auth_service):
        """Test OTP is properly hashed with Argon2id."""
        otp = "123456"

        # Hash the OTP
        otp_hash = auth_service.hash_otp(otp)

        # Should not be the same as original
        assert otp_hash != otp, "Hash should be different from original OTP"

        # Should be Argon2id format
        assert otp_hash.startswith("$argon2id$"), "Hash should be in Argon2id format"

        # Should verify correctly
        assert auth_service.verify_otp_hash(otp, otp_hash), (
            "Hash should verify correctly"
        )

        # Should not verify with wrong OTP
        assert not auth_service.verify_otp_hash("654321", otp_hash), (
            "Wrong OTP should not verify"
        )

    def test_otp_hashing_error_handling(self, auth_service):
        """Test OTP hashing error handling."""
        with patch("os.urandom", side_effect=Exception("Random generation failed")):
            with pytest.raises(Exception):
                auth_service.hash_otp("123456")

    def test_verify_otp_hash_mismatch(self, auth_service):
        """Test OTP verification with wrong code."""
        otp = "123456"
        otp_hash = auth_service.hash_otp(otp)

        # Wrong OTP should return False
        assert not auth_service.verify_otp_hash("654321", otp_hash)

    def test_verify_otp_hash_error_handling(self, auth_service):
        """Test OTP verification error handling."""
        # Test with invalid hash format
        assert not auth_service.verify_otp_hash("123456", "invalid_hash")

    def test_rate_limiting_email_comprehensive(self, auth_service, mock_redis_client):
        """Test email rate limiting (3/hour per email)."""
        email = "test@example.com"
        telegram_id = 123456789

        # Test exactly 3 sends allowed per hour
        mock_redis_client.check_email_rate_limit.return_value = (
            True,
            2,
        )  # 2 previous sends
        allowed, reason = auth_service.check_rate_limits(telegram_id, email)
        assert allowed, "Should allow 3rd send"

        # Test 4th send blocked with proper error
        mock_redis_client.check_email_rate_limit.return_value = (
            False,
            3,
        )  # 3 previous sends
        allowed, reason = auth_service.check_rate_limits(telegram_id, email)
        assert not allowed, "Should block 4th send"
        assert "email_limit_exceeded" in reason, (
            f"Should indicate email limit exceeded, got: {reason}"
        )

    def test_rate_limiting_user_comprehensive(self, auth_service, mock_redis_client):
        """Test user rate limiting (5/hour per telegram_id)."""
        email = "test@example.com"
        telegram_id = 123456789

        # Test exactly 5 sends allowed per hour per user
        mock_redis_client.check_user_rate_limit.return_value = (
            True,
            4,
        )  # 4 previous sends
        allowed, reason = auth_service.check_rate_limits(telegram_id, email)
        assert allowed, "Should allow 5th send"

        # Test 6th send blocked with proper error
        mock_redis_client.check_user_rate_limit.return_value = (
            False,
            5,
        )  # 5 previous sends
        allowed, reason = auth_service.check_rate_limits(telegram_id, email)
        assert not allowed, "Should block 6th send"
        assert "user_limit_exceeded" in reason, (
            f"Should indicate user limit exceeded, got: {reason}"
        )

    def test_rate_limiting_spacing_comprehensive(self, auth_service, mock_redis_client):
        """Test 60s spacing between OTP sends per telegram_id."""
        email = "test@example.com"
        telegram_id = 123456789

        # Test send blocked if <60s since last send
        mock_redis_client.check_spacing_limit.return_value = (
            False,
            30,
        )  # 30s since last
        allowed, reason = auth_service.check_rate_limits(telegram_id, email)
        assert not allowed, "Should block send if <60s since last"
        assert "spacing_violation" in reason, (
            f"Should indicate spacing violation, got: {reason}"
        )

        # Test send allowed if ≥60s since last send
        mock_redis_client.check_spacing_limit.return_value = (
            True,
            60,
        )  # 60s since last
        allowed, reason = auth_service.check_rate_limits(telegram_id, email)
        assert allowed, "Should allow send if ≥60s since last"

    def test_send_otp_invalid_email(self, auth_service):
        """Test OTP sending with invalid email format."""
        telegram_id = 123456789
        invalid_email = "invalid-email"

        success, message, otp = auth_service.send_otp(telegram_id, invalid_email)

        assert not success, "Should fail with invalid email"
        assert message == "invalid_email_format", (
            f"Should indicate invalid email format, got: {message}"
        )
        assert otp is None, "Should not return OTP for invalid email"

    def test_send_otp_rate_limited(self, auth_service, mock_redis_client):
        """Test OTP sending when rate limited."""
        telegram_id = 123456789
        email = "test@example.com"

        # Mock rate limit exceeded
        mock_redis_client.check_email_rate_limit.return_value = (False, 3)

        success, message, otp = auth_service.send_otp(telegram_id, email)

        assert not success, "Should fail when rate limited"
        assert "rate_limited" in message, (
            f"Should indicate rate limiting, got: {message}"
        )
        assert otp is None, "Should not return OTP when rate limited"

    def test_send_otp_success(self, auth_service, mock_redis_client):
        """Test successful OTP sending with complete OTP context storage."""
        telegram_id = 123456789
        email = "Test@Example.Com"  # Original format with mixed case
        expected_normalized = "test@example.com"

        # Mock the enhanced method
        mock_redis_client.store_otp_with_original = Mock(return_value=True)

        success, message, otp = auth_service.send_otp(telegram_id, email)

        assert success, f"Should succeed, got message: {message}"
        assert message == "otp_sent", f"Should indicate OTP sent, got: {message}"
        assert otp is not None, "Should return OTP for testing"
        assert len(otp) == 6, "Should return 6-digit OTP"
        assert otp.isdigit(), "Should return numeric OTP"

        # Verify Redis operations were called with complete OTP context
        mock_redis_client.store_otp_with_original.assert_called_once()
        call_args = mock_redis_client.store_otp_with_original.call_args
        # Arguments are positional: (telegram_id, otp_hash, normalized_email, original_email, ttl)
        assert call_args[0][0] == telegram_id  # telegram_id
        assert call_args[0][2] == expected_normalized  # normalized_email
        assert call_args[0][3] == email  # original_email
        assert call_args[0][4] == 300  # ttl

        mock_redis_client.increment_rate_limits.assert_called_once_with(
            telegram_id, expected_normalized
        )

    def test_send_otp_storage_failure(self, auth_service, mock_redis_client):
        """Test OTP sending when Redis storage fails."""
        telegram_id = 123456789
        email = "test@example.com"

        # Mock storage failure - use the correct method name
        mock_redis_client.store_otp_with_original = Mock(return_value=False)

        success, message, otp = auth_service.send_otp(telegram_id, email)

        assert not success, "Should fail when storage fails"
        assert message == "storage_failed", (
            f"Should indicate storage failure, got: {message}"
        )
        assert otp is None, "Should not return OTP when storage fails"

    def test_verify_otp_not_found(self, auth_service, mock_redis_client):
        """Test OTP verification when OTP not found or expired."""
        telegram_id = 123456789
        otp = "123456"

        # Mock OTP not found
        mock_redis_client.get_otp_data.return_value = None

        success, message = auth_service.verify_otp(telegram_id, otp)

        assert not success, "Should fail when OTP not found"
        assert message == "otp_not_found_or_expired", (
            f"Should indicate OTP not found, got: {message}"
        )

    def test_verify_otp_expired(self, auth_service, mock_redis_client):
        """Test OTP verification after 5-minute expiry with proper key cleanup."""
        telegram_id = 123456789
        otp = "123456"

        # Mock expired OTP data with complete context
        expired_time = int(time.time()) - 100  # 100 seconds ago
        mock_redis_client.get_otp_data.return_value = {
            "otp_hash": "hash",
            "normalized_email": "test@example.com",
            "email_original": "Test@Example.Com",
            "expires_at": expired_time,
            "attempts": 0,
        }

        success, message = auth_service.verify_otp(telegram_id, otp)

        assert not success, "Should fail when OTP expired"
        assert message == "otp_expired", f"Should indicate OTP expired, got: {message}"

        # Should delete expired OTP with proper reason
        mock_redis_client.delete_otp.assert_called_once_with(telegram_id, "expired")

    def test_verify_otp_attempt_limit_exceeded(self, auth_service, mock_redis_client):
        """Test OTP verification attempt limit (3 attempts) with proper key cleanup."""
        telegram_id = 123456789
        otp = "123456"

        # Mock valid OTP data with complete context
        future_time = int(time.time()) + 300
        mock_redis_client.get_otp_data.return_value = {
            "otp_hash": "hash",
            "normalized_email": "test@example.com",
            "email_original": "Test@Example.Com",
            "expires_at": future_time,
            "attempts": 0,
        }

        # Mock attempt counter returning 4 (exceeded limit)
        mock_redis_client.increment_otp_attempts.return_value = 4

        success, message = auth_service.verify_otp(telegram_id, otp)

        assert not success, "Should fail when attempt limit exceeded"
        assert message == "attempt_limit_exceeded", (
            f"Should indicate attempt limit exceeded, got: {message}"
        )

        # Should delete OTP after attempt limit exceeded with proper reason
        mock_redis_client.delete_otp.assert_called_once_with(
            telegram_id, "attempt_limit_exceeded"
        )

    def test_verify_otp_invalid_code(self, auth_service, mock_redis_client):
        """Test OTP verification with wrong code and attempt counter increment."""
        telegram_id = 123456789
        otp = "123456"
        correct_otp = "654321"

        # Create real hash for testing
        otp_hash = auth_service.hash_otp(correct_otp)

        # Mock valid OTP data with complete context and real hash
        future_time = int(time.time()) + 300
        mock_redis_client.get_otp_data.return_value = {
            "otp_hash": otp_hash,
            "normalized_email": "test@example.com",
            "email_original": "Test@Example.Com",
            "expires_at": future_time,
            "attempts": 0,
        }

        # Mock attempt counter returning 1 (first attempt)
        mock_redis_client.increment_otp_attempts.return_value = 1

        success, message = auth_service.verify_otp(telegram_id, otp)

        assert not success, "Should fail with wrong OTP"
        assert "invalid_otp_attempt_1" in message, (
            f"Should indicate invalid OTP with attempt count, got: {message}"
        )

        # Should increment attempts on every verification attempt
        mock_redis_client.increment_otp_attempts.assert_called_once_with(telegram_id)

        # Should NOT delete OTP on failed attempt (unless 3rd attempt)
        mock_redis_client.delete_otp.assert_not_called()

    def test_verify_otp_invalid_code_third_attempt(
        self, auth_service, mock_redis_client
    ):
        """Test OTP verification with wrong code on 3rd attempt - delete key after >3 failed attempts."""
        telegram_id = 123456789
        otp = "123456"
        correct_otp = "654321"

        # Create real hash for testing
        otp_hash = auth_service.hash_otp(correct_otp)

        # Mock valid OTP data with complete context and real hash
        future_time = int(time.time()) + 300
        mock_redis_client.get_otp_data.return_value = {
            "otp_hash": otp_hash,
            "normalized_email": "test@example.com",
            "email_original": "Test@Example.Com",
            "expires_at": future_time,
            "attempts": 0,
        }

        # Mock attempt counter returning 3 (third attempt)
        mock_redis_client.increment_otp_attempts.return_value = 3

        success, message = auth_service.verify_otp(telegram_id, otp)

        assert not success, "Should fail with wrong OTP"
        assert message == "attempt_limit_exceeded", (
            f"Should indicate attempt limit exceeded, got: {message}"
        )

        # Should increment attempts on every verification attempt
        mock_redis_client.increment_otp_attempts.assert_called_once_with(telegram_id)

        # Should delete OTP key after >3 failed attempts with proper reason
        mock_redis_client.delete_otp.assert_called_once_with(
            telegram_id, "attempt_limit_exceeded"
        )

    @patch("src.auth_service.get_db_session")
    def test_verify_otp_success_new_user_first_verification(
        self, mock_get_session, auth_service, mock_redis_client
    ):
        """Test successful OTP verification for new user (first-time verification)."""
        telegram_id = 123456789
        otp = "123456"
        email = "test@example.com"
        email_original = "Test@Example.Com"

        # Create real hash for testing
        otp_hash = auth_service.hash_otp(otp)

        # Mock valid OTP data with complete context and real hash
        future_time = int(time.time()) + 300
        mock_redis_client.get_otp_data.return_value = {
            "otp_hash": otp_hash,
            "normalized_email": email,
            "email_original": email_original,
            "expires_at": future_time,
            "attempts": 0,
        }

        # Mock attempt counter returning 1 (first attempt)
        mock_redis_client.increment_otp_attempts.return_value = 1

        # Mock database session
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        # Mock no existing user by telegram_id
        mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            None,  # No user by telegram_id
            None,  # No user by email (for uniqueness check)
        ]

        success, message = auth_service.verify_otp(telegram_id, otp)

        assert success, f"Should succeed with correct OTP, got message: {message}"
        assert message == "verification_successful", (
            f"Should indicate success, got: {message}"
        )

        # Should delete OTP key on successful verification with proper reason
        mock_redis_client.delete_otp.assert_called_once_with(
            telegram_id, "verification_success"
        )

        # Should create new user with proper fields and log auth event
        assert mock_session.add.call_count == 2, "Should add both User and AuthEvent"

        # Check the User object (first call)
        user_call = mock_session.add.call_args_list[0]
        added_user = user_call[0][0]
        assert added_user.telegram_id == telegram_id
        assert added_user.email == email  # Normalized
        assert added_user.email_original == email_original  # Original format
        assert added_user.is_authenticated == True
        assert added_user.email_verified_at is not None
        assert added_user.last_authenticated_at is not None

        # Check the AuthEvent object (second call)
        event_call = mock_session.add.call_args_list[1]
        added_event = event_call[0][0]
        assert added_event.telegram_id == telegram_id
        assert added_event.event_type == "OTP_VERIFIED"
        assert added_event.success == True

        mock_session.commit.assert_called()

    @patch("src.auth_service.get_db_session")
    def test_verify_otp_success_existing_user_first_verification(
        self, mock_get_session, auth_service, mock_redis_client
    ):
        """Test successful OTP verification for existing user (first-time email verification)."""
        telegram_id = 123456789
        otp = "123456"
        email = "test@example.com"
        email_original = "Test@Example.Com"

        # Create real hash for testing
        otp_hash = auth_service.hash_otp(otp)

        # Mock valid OTP data with complete context and real hash
        future_time = int(time.time()) + 300
        mock_redis_client.get_otp_data.return_value = {
            "otp_hash": otp_hash,
            "normalized_email": email,
            "email_original": email_original,
            "expires_at": future_time,
            "attempts": 0,
        }

        # Mock attempt counter returning 1 (first attempt)
        mock_redis_client.increment_otp_attempts.return_value = 1

        # Mock database session with existing user (never verified email before)
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_user = Mock()
        mock_user.email_verified_at = None  # Never verified before
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            mock_user
        )

        success, message = auth_service.verify_otp(telegram_id, otp)

        assert success, f"Should succeed with correct OTP, got message: {message}"
        assert message == "verification_successful", (
            f"Should indicate success, got: {message}"
        )

        # Should delete OTP key on successful verification with proper reason
        mock_redis_client.delete_otp.assert_called_once_with(
            telegram_id, "verification_success"
        )

        # Should update existing user with first-time verification
        assert mock_user.email == email  # Normalized
        assert mock_user.email_original == email_original  # Original format
        assert mock_user.is_authenticated == True
        assert mock_user.email_verified_at is not None  # Should be set for first time
        assert mock_user.last_authenticated_at is not None
        assert mock_session.commit.call_count == 2  # User update + audit event

    @patch("src.auth_service.get_db_session")
    def test_verify_otp_success_existing_user_subsequent_verification(
        self, mock_get_session, auth_service, mock_redis_client
    ):
        """Test successful OTP verification for existing user (subsequent verification)."""
        telegram_id = 123456789
        otp = "123456"
        email = "test@example.com"
        email_original = "Test@Example.Com"

        # Create real hash for testing
        otp_hash = auth_service.hash_otp(otp)

        # Mock valid OTP data with complete context and real hash
        future_time = int(time.time()) + 300
        mock_redis_client.get_otp_data.return_value = {
            "otp_hash": otp_hash,
            "normalized_email": email,
            "email_original": email_original,
            "expires_at": future_time,
            "attempts": 0,
        }

        # Mock attempt counter returning 1 (first attempt)
        mock_redis_client.increment_otp_attempts.return_value = 1

        # Mock database session with existing user (already verified before)
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_user = Mock()

        # User was already verified before (has email_verified_at timestamp)
        from datetime import datetime, timezone

        original_verified_at = datetime.now(timezone.utc)
        mock_user.email_verified_at = original_verified_at

        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            mock_user
        )

        success, message = auth_service.verify_otp(telegram_id, otp)

        assert success, f"Should succeed with correct OTP, got message: {message}"
        assert message == "verification_successful", (
            f"Should indicate success, got: {message}"
        )

        # Should delete OTP key on successful verification with proper reason
        mock_redis_client.delete_otp.assert_called_once_with(
            telegram_id, "verification_success"
        )

        # Should update existing user for subsequent verification
        assert mock_user.email == email  # Normalized
        assert mock_user.email_original == email_original  # Original format
        assert mock_user.is_authenticated == True
        # email_verified_at should NOT be changed (keep original timestamp)
        assert mock_user.email_verified_at == original_verified_at
        assert mock_user.last_authenticated_at is not None  # Should be updated
        assert mock_session.commit.call_count == 2  # User update + audit event

    @patch("src.auth_service.get_db_session")
    def test_persist_authentication_email_conflict(
        self, mock_get_session, auth_service, mock_redis_client
    ):
        """Test authentication persistence when email already exists for different user."""
        telegram_id = 123456789
        otp = "123456"
        email = "test@example.com"
        email_original = "Test@Example.Com"

        # Create real hash for testing
        otp_hash = auth_service.hash_otp(otp)

        # Mock valid OTP data with complete context
        future_time = int(time.time()) + 300
        mock_redis_client.get_otp_data.return_value = {
            "otp_hash": otp_hash,
            "normalized_email": email,
            "email_original": email_original,
            "expires_at": future_time,
            "attempts": 0,
        }

        # Mock attempt counter returning 1 (first attempt)
        mock_redis_client.increment_otp_attempts.return_value = 1

        # Mock database session
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        # Mock existing user with different telegram_id but same email
        existing_user = Mock()
        existing_user.telegram_id = 987654321  # Different telegram_id

        mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            None,  # No user by telegram_id
            existing_user,  # User exists with same email
        ]

        success, message = auth_service.verify_otp(telegram_id, otp)

        assert not success, "Should fail when email already exists for different user"
        assert message == "persistence_failed", (
            f"Should indicate persistence failure, got: {message}"
        )

        # Should still delete OTP key after verification attempt with proper reason
        mock_redis_client.delete_otp.assert_called_once_with(
            telegram_id, "verification_success"
        )

    @patch("src.auth_service.get_db_session")
    def test_is_user_authenticated_true(self, mock_get_session, auth_service):
        """Test checking authentication status for authenticated user."""
        telegram_id = 123456789

        # Mock database session with authenticated user
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_user = Mock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            mock_user
        )

        result = auth_service.is_user_authenticated(telegram_id)

        assert result == True, "Should return True for authenticated user"

    @patch("src.auth_service.get_db_session")
    def test_is_user_authenticated_false(self, mock_get_session, auth_service):
        """Test checking authentication status for non-authenticated user."""
        telegram_id = 123456789

        # Mock database session with no user found
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        result = auth_service.is_user_authenticated(telegram_id)

        assert result == False, "Should return False for non-authenticated user"

    @patch("src.auth_service.get_db_session")
    def test_get_user_email_success(self, mock_get_session, auth_service):
        """Test getting user email for authenticated user."""
        telegram_id = 123456789
        expected_email = "test@example.com"

        # Mock database session with authenticated user
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_user = Mock()
        mock_user.email = expected_email
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            mock_user
        )

        result = auth_service.get_user_email(telegram_id)

        assert result == expected_email, f"Should return user email, got: {result}"

    @patch("src.auth_service.get_db_session")
    def test_get_user_email_not_found(self, mock_get_session, auth_service):
        """Test getting user email for non-authenticated user."""
        telegram_id = 123456789

        # Mock database session with no user found
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        result = auth_service.get_user_email(telegram_id)

        assert result is None, "Should return None for non-authenticated user"

    def test_redis_otp_complete_context_storage(self, auth_service, mock_redis_client):
        """Test that complete OTP context is stored in Redis as per task 2.5."""
        telegram_id = 123456789
        email = "Test@Example.Com"
        expected_normalized = "test@example.com"

        # Mock the enhanced method
        mock_redis_client.store_otp_with_original = Mock(return_value=True)

        success, message, otp = auth_service.send_otp(telegram_id, email)

        assert success, f"Should succeed, got message: {message}"

        # Verify complete OTP context is stored with all required fields
        mock_redis_client.store_otp_with_original.assert_called_once()
        call_args = mock_redis_client.store_otp_with_original.call_args

        # Verify positional arguments are correct
        args = call_args[0]
        assert args[0] == telegram_id  # telegram_id
        assert args[2] == expected_normalized  # normalized email
        assert args[3] == email  # original email format
        assert args[4] == 300  # ttl
        assert len(args[1]) > 0  # OTP hash should be present and non-empty

    def test_attempt_counter_increment_and_persistence(
        self, auth_service, mock_redis_client
    ):
        """Test attempt counter increment and persistence on every verification attempt."""
        telegram_id = 123456789
        otp = "123456"
        correct_otp = "654321"

        # Create real hash for testing
        otp_hash = auth_service.hash_otp(correct_otp)

        # Mock valid OTP data with complete context
        future_time = int(time.time()) + 300
        mock_redis_client.get_otp_data.return_value = {
            "otp_hash": otp_hash,
            "normalized_email": "test@example.com",
            "email_original": "Test@Example.Com",
            "expires_at": future_time,
            "attempts": 0,
        }

        # Mock attempt counter returning 2 (second attempt)
        mock_redis_client.increment_otp_attempts.return_value = 2

        success, message = auth_service.verify_otp(telegram_id, otp)

        assert not success, "Should fail with wrong OTP"
        assert "invalid_otp_attempt_2" in message, (
            f"Should indicate invalid OTP with attempt count, got: {message}"
        )

        # Verify attempt counter is incremented on every verification attempt
        mock_redis_client.increment_otp_attempts.assert_called_once_with(telegram_id)

        # Should NOT delete OTP on failed attempt (unless 3rd attempt)
        mock_redis_client.delete_otp.assert_not_called()

    def test_otp_key_cleanup_on_success(self, auth_service, mock_redis_client):
        """Test OTP key deletion on successful verification."""
        telegram_id = 123456789
        otp = "123456"

        # Create real hash for testing
        otp_hash = auth_service.hash_otp(otp)

        # Mock valid OTP data with complete context
        future_time = int(time.time()) + 300
        mock_redis_client.get_otp_data.return_value = {
            "otp_hash": otp_hash,
            "normalized_email": "test@example.com",
            "email_original": "Test@Example.Com",
            "expires_at": future_time,
            "attempts": 0,
        }

        # Mock attempt counter returning 1 (first attempt)
        mock_redis_client.increment_otp_attempts.return_value = 1

        # Mock successful database persistence
        with patch("src.auth_service.get_db_session") as mock_get_session:
            mock_session = Mock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter_by.return_value.first.side_effect = [
                None,  # No user by telegram_id
                None,  # No user by email (for uniqueness check)
            ]

            success, message = auth_service.verify_otp(telegram_id, otp)

            assert success, f"Should succeed with correct OTP, got message: {message}"

            # Verify OTP key is deleted on successful verification with proper reason
            mock_redis_client.delete_otp.assert_called_once_with(
                telegram_id, "verification_success"
            )

    def test_otp_key_cleanup_on_max_attempts(self, auth_service, mock_redis_client):
        """Test OTP key deletion after >3 failed attempts."""
        telegram_id = 123456789
        otp = "123456"
        correct_otp = "654321"

        # Create real hash for testing
        otp_hash = auth_service.hash_otp(correct_otp)

        # Mock valid OTP data with complete context
        future_time = int(time.time()) + 300
        mock_redis_client.get_otp_data.return_value = {
            "otp_hash": otp_hash,
            "normalized_email": "test@example.com",
            "email_original": "Test@Example.Com",
            "expires_at": future_time,
            "attempts": 0,
        }

        # Mock attempt counter returning 3 (third attempt - at limit)
        mock_redis_client.increment_otp_attempts.return_value = 3

        success, message = auth_service.verify_otp(telegram_id, otp)

        assert not success, "Should fail with wrong OTP"
        assert message == "attempt_limit_exceeded", (
            f"Should indicate attempt limit exceeded, got: {message}"
        )

        # Verify OTP key is deleted after >3 failed attempts with proper reason
        mock_redis_client.delete_otp.assert_called_once_with(
            telegram_id, "attempt_limit_exceeded"
        )

    def test_otp_key_cleanup_on_expiry(self, auth_service, mock_redis_client):
        """Test OTP key deletion on expiry."""
        telegram_id = 123456789
        otp = "123456"

        # Mock expired OTP data with complete context
        expired_time = int(time.time()) - 100  # 100 seconds ago
        mock_redis_client.get_otp_data.return_value = {
            "otp_hash": "hash",
            "normalized_email": "test@example.com",
            "email_original": "Test@Example.Com",
            "expires_at": expired_time,
            "attempts": 0,
        }

        success, message = auth_service.verify_otp(telegram_id, otp)

        assert not success, "Should fail when OTP expired"
        assert message == "otp_expired", f"Should indicate OTP expired, got: {message}"

        # Verify OTP key is deleted on expiry with proper reason
        mock_redis_client.delete_otp.assert_called_once_with(telegram_id, "expired")


class TestAuthServiceGlobals:
    """Test global auth service initialization and access."""

    def test_init_auth_service(self):
        """Test auth service initialization."""
        from src.config import BotConfig

        mock_config = Mock()
        mock_config.otp_ttl_seconds = 300
        mock_config.otp_max_attempts = 3
        mock_config.email_rate_limit_per_hour = 3
        mock_config.user_rate_limit_per_hour = 5
        mock_config.otp_spacing_seconds = 60

        with patch("src.auth_service.get_redis_client"):
            service = init_auth_service(mock_config)
            assert service is not None
            assert isinstance(service, AuthService)

    def test_get_auth_service_not_initialized(self):
        """Test getting auth service when not initialized."""
        # Reset global state
        import src.auth_service

        src.auth_service.auth_service = None

        with pytest.raises(RuntimeError, match="Auth service not initialized"):
            get_auth_service()

    def test_get_auth_service_initialized(self):
        """Test getting auth service when initialized."""
        from src.config import BotConfig

        mock_config = Mock()
        mock_config.otp_ttl_seconds = 300
        mock_config.otp_max_attempts = 3
        mock_config.email_rate_limit_per_hour = 3
        mock_config.user_rate_limit_per_hour = 5
        mock_config.otp_spacing_seconds = 60

        with patch("src.auth_service.get_redis_client"):
            service = init_auth_service(mock_config)
            retrieved_service = get_auth_service()
            assert retrieved_service is service
