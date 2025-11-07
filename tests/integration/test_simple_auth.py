"""
Simple test for auth service OTP generation and hashing without Redis dependency.
"""

import os
import sys

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# Mock redis module - skip this test as it's redundant with test_auth_service.py
pytest.skip(
    "Skipping legacy test - functionality covered by test_auth_service.py",
    allow_module_level=True,
)


# Mock the database functions to avoid database dependency
def mock_get_db_session():
    class MockSession:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def query(self, model):
            class MockQuery:
                def filter_by(self, **kwargs):
                    class MockResult:
                        def first(self):
                            return None

                    return MockResult()

            return MockQuery()

        def add(self, obj):
            pass

        def commit(self):
            pass

    return MockSession()


def mock_normalize_email(email):
    return email.lower() if email else ""


# Mock the database imports
import telegram_bot.database


telegram_bot.data.database.get_db_session = mock_get_db_session
telegram_bot.data.database.normalize_email = mock_normalize_email


# Mock the redis client to avoid import issues
class MockRedisClient:
    def check_email_rate_limit(self, email, limit=3):
        return True, 0

    def check_user_rate_limit(self, telegram_id, limit=5):
        return True, 0

    def check_spacing_limit(self, telegram_id, min_spacing=60):
        return True, 60

    def store_otp(self, telegram_id, otp_hash, email, ttl=300):
        return True

    def increment_rate_limits(self, telegram_id, email):
        return True


# Mock the get_redis_client function
def mock_get_redis_client():
    return MockRedisClient()


# Patch the import before importing auth_service
import telegram_bot.auth_service


telegram_bot.auth.auth_service.get_redis_client = mock_get_redis_client

from telegram_bot.auth.auth_service import AuthService


def test_otp_generation():
    """Test OTP generation creates 6-digit numeric code."""
    auth_service = AuthService()

    for _ in range(10):  # Test multiple generations
        otp = auth_service.generate_otp()

        # Should be exactly 6 digits
        assert len(otp) == 6, f"OTP should be 6 digits, got: {otp}"

        # Should be numeric
        assert otp.isdigit(), f"OTP should be numeric, got: {otp}"

        # Should be in valid range (100000-999999)
        otp_int = int(otp)
        assert 100000 <= otp_int <= 999999, f"OTP should be 6 digits, got: {otp_int}"

    print("✓ OTP generation test passed")


def test_otp_hashing():
    """Test OTP hashing and verification."""
    auth_service = AuthService()
    otp = "123456"

    # Hash the OTP
    otp_hash = auth_service.hash_otp(otp)

    # Should not be the same as original
    assert otp_hash != otp, "Hash should be different from original OTP"

    # Should be base64 encoded
    import base64

    try:
        decoded = base64.b64decode(otp_hash)
        assert len(decoded) == 32 + 32, "Should contain 32-byte salt + 32-byte hash"
    except Exception:
        assert False, "Hash should be valid base64"

    # Should verify correctly
    assert auth_service.verify_otp_hash(otp, otp_hash), "Hash should verify correctly"

    # Should not verify with wrong OTP
    assert not auth_service.verify_otp_hash("654321", otp_hash), "Wrong OTP should not verify"

    print("✓ OTP hashing test passed")


def test_email_validation():
    """Test email format validation."""
    auth_service = AuthService()

    # Valid emails
    valid_emails = [
        "test@example.com",
        "user.name@domain.co.uk",
        "user+tag@example.org",
        "123@test.com",
        "a@b.co",
    ]

    for email in valid_emails:
        assert auth_service.validate_email_format(email), f"Should accept valid email: {email}"

    # Invalid emails
    invalid_emails = ["", "invalid", "@example.com", "user@", "user@domain", None]

    for email in invalid_emails:
        assert not auth_service.validate_email_format(email), (
            f"Should reject invalid email: {email}"
        )

    print("✓ Email validation test passed")


if __name__ == "__main__":
    test_otp_generation()
    test_otp_hashing()
    test_email_validation()
    print("\n🎉 All tests passed!")


def test_rate_limiting():
    """Test comprehensive rate limiting functionality."""
    auth_service = AuthService()

    # Test rate limit checking
    telegram_id = 123456789
    email = "test@example.com"

    # Should pass rate limits initially
    allowed, reason = auth_service.check_rate_limits(telegram_id, email)
    assert allowed, f"Should allow initial request, got reason: {reason}"

    print("✓ Rate limiting test passed")


def test_send_otp_basic():
    """Test basic OTP sending functionality."""
    auth_service = AuthService()

    telegram_id = 123456789
    email = "test@example.com"

    # Should succeed with valid email
    success, message, otp = auth_service.send_otp(telegram_id, email)
    assert success, f"Should succeed with valid email, got message: {message}"
    assert otp is not None, "Should return OTP for testing"
    assert len(otp) == 6, "Should return 6-digit OTP"
    assert otp.isdigit(), "Should return numeric OTP"

    # Should fail with invalid email
    success, message, otp = auth_service.send_otp(telegram_id, "invalid-email")
    assert not success, "Should fail with invalid email"
    assert message == "invalid_email_format", (
        f"Should indicate invalid email format, got: {message}"
    )
    assert otp is None, "Should not return OTP for invalid email"

    print("✓ Send OTP basic test passed")


if __name__ == "__main__":
    test_otp_generation()
    test_otp_hashing()
    test_email_validation()
    test_rate_limiting()
    test_send_otp_basic()
    print("\n🎉 All tests passed!")


def test_otp_verification_system():
    """Test comprehensive OTP verification functionality."""

    # Create a more sophisticated mock Redis client for verification testing
    class VerificationMockRedisClient:
        def __init__(self):
            self.otp_data = {}

        def check_email_rate_limit(self, email, limit=3):
            return True, 0

        def check_user_rate_limit(self, telegram_id, limit=5):
            return True, 0

        def check_spacing_limit(self, telegram_id, min_spacing=60):
            return True, 60

        def store_otp(self, telegram_id, otp_hash, email, ttl=300):
            import time

            self.otp_data[telegram_id] = {
                "otp_hash": otp_hash,
                "email": email,
                "expires_at": int(time.time()) + ttl,
                "attempts": 0,
            }
            return True

        def increment_rate_limits(self, telegram_id, email):
            return True

        def get_otp_data(self, telegram_id):
            return self.otp_data.get(telegram_id)

        def increment_otp_attempts(self, telegram_id):
            if telegram_id in self.otp_data:
                self.otp_data[telegram_id]["attempts"] += 1
                return self.otp_data[telegram_id]["attempts"]
            return -1

        def delete_otp(self, telegram_id):
            if telegram_id in self.otp_data:
                del self.otp_data[telegram_id]
                return True
            return False

    # Create auth service with verification mock
    verification_redis_client = VerificationMockRedisClient()

    # Patch the auth service to use our verification mock
    import telegram_bot.auth_service

    original_get_redis_client = telegram_bot.auth.auth_service.get_redis_client
    telegram_bot.auth.auth_service.get_redis_client = lambda: verification_redis_client

    try:
        auth_service = AuthService()
        telegram_id = 123456789
        email = "test@example.com"

        # First, send an OTP
        success, message, otp = auth_service.send_otp(telegram_id, email)
        assert success, f"Should succeed sending OTP, got message: {message}"
        assert otp is not None, "Should return OTP for testing"

        # Test successful verification
        success, message = auth_service.verify_otp(telegram_id, otp)
        assert success, f"Should succeed with correct OTP, got message: {message}"
        assert message == "verification_successful", f"Should indicate success, got: {message}"

        # Test verification with non-existent OTP
        success, message = auth_service.verify_otp(999999999, "123456")
        assert not success, "Should fail with non-existent OTP"
        assert message == "otp_not_found_or_expired", (
            f"Should indicate OTP not found, got: {message}"
        )

        # Test verification with wrong OTP (need to send new OTP first)
        success, message, otp = auth_service.send_otp(telegram_id, email)
        assert success, "Should succeed sending new OTP"

        success, message = auth_service.verify_otp(telegram_id, "999999")
        assert not success, "Should fail with wrong OTP"
        assert "invalid_otp_attempt" in message, (
            f"Should indicate invalid OTP attempt, got: {message}"
        )

        print("✓ OTP verification system test passed")

    finally:
        # Restore original function
        telegram_bot.auth.auth_service.get_redis_client = original_get_redis_client


if __name__ == "__main__":
    test_otp_generation()
    test_otp_hashing()
    test_email_validation()
    test_rate_limiting()
    test_send_otp_basic()
    test_otp_verification_system()
    print("\n🎉 All tests passed!")


def test_authentication_persistence():
    """Test authentication state persistence functionality."""

    # Create a mock database session that tracks user creation/updates
    class PersistenceMockSession:
        def __init__(self):
            self.users = {}
            self.added_users = []
            self.committed = False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def query(self, model):
            class MockQuery:
                def __init__(self, session):
                    self.session = session

                def filter_by(self, **kwargs):
                    class MockResult:
                        def __init__(self, session, filters):
                            self.session = session
                            self.filters = filters

                        def first(self):
                            telegram_id = self.filters.get("telegram_id")
                            if telegram_id in self.session.users:
                                return self.session.users[telegram_id]
                            return None

                    return MockResult(self.session, kwargs)

            return MockQuery(self)

        def add(self, user):
            self.added_users.append(user)
            self.users[user.telegram_id] = user

        def commit(self):
            self.committed = True

    # Mock the database session
    persistence_session = PersistenceMockSession()

    def mock_get_db_session_persistence():
        return persistence_session

    # Patch the database function
    import telegram_bot.auth_service

    original_get_db_session = telegram_bot.auth.auth_service.get_db_session
    telegram_bot.auth.auth_service.get_db_session = mock_get_db_session_persistence

    try:
        auth_service = AuthService()
        telegram_id = 123456789
        email = "test@example.com"

        # Test persisting authentication for new user
        success = auth_service.persist_authentication(telegram_id, email)
        assert success, "Should succeed persisting authentication for new user"
        assert len(persistence_session.added_users) == 1, "Should add one new user"
        assert persistence_session.committed, "Should commit the transaction"

        new_user = persistence_session.added_users[0]
        assert new_user.telegram_id == telegram_id, "Should set correct telegram_id"
        assert new_user.email == email, "Should set correct email"
        assert new_user.is_authenticated == True, "Should set is_authenticated to True"
        assert new_user.email_verified_at is not None, "Should set email_verified_at"
        assert new_user.last_authenticated_at is not None, "Should set last_authenticated_at"

        # Test persisting authentication for existing user
        persistence_session.committed = False  # Reset commit flag
        success = auth_service.persist_authentication(telegram_id, email)
        assert success, "Should succeed persisting authentication for existing user"
        assert persistence_session.committed, "Should commit the transaction"

        # The existing user should be updated
        existing_user = persistence_session.users[telegram_id]
        assert existing_user.is_authenticated == True, "Should update is_authenticated to True"
        assert existing_user.last_authenticated_at is not None, (
            "Should update last_authenticated_at"
        )

        print("✓ Authentication persistence test passed")

    finally:
        # Restore original function
        telegram_bot.auth.auth_service.get_db_session = original_get_db_session


def test_user_authentication_status():
    """Test checking user authentication status."""

    # Create a mock database session for authentication status testing
    class AuthStatusMockSession:
        def __init__(self):
            self.authenticated_users = set()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def query(self, model):
            class MockQuery:
                def __init__(self, session):
                    self.session = session

                def filter_by(self, **kwargs):
                    class MockResult:
                        def __init__(self, session, filters):
                            self.session = session
                            self.filters = filters

                        def first(self):
                            telegram_id = self.filters.get("telegram_id")
                            is_authenticated = self.filters.get("is_authenticated")
                            if telegram_id in self.session.authenticated_users and is_authenticated:
                                # Return a mock user object
                                class MockUser:
                                    def __init__(self, telegram_id, email):
                                        self.telegram_id = telegram_id
                                        self.email = email

                                return MockUser(telegram_id, "test@example.com")
                            return None

                    return MockResult(self.session, kwargs)

            return MockQuery(self)

    # Mock the database session
    auth_status_session = AuthStatusMockSession()

    def mock_get_db_session_auth_status():
        return auth_status_session

    # Patch the database function
    import telegram_bot.auth_service

    original_get_db_session = telegram_bot.auth.auth_service.get_db_session
    telegram_bot.auth.auth_service.get_db_session = mock_get_db_session_auth_status

    try:
        auth_service = AuthService()
        telegram_id = 123456789

        # Test non-authenticated user
        is_authenticated = auth_service.is_user_authenticated(telegram_id)
        assert not is_authenticated, "Should return False for non-authenticated user"

        # Test authenticated user
        auth_status_session.authenticated_users.add(telegram_id)
        is_authenticated = auth_service.is_user_authenticated(telegram_id)
        assert is_authenticated, "Should return True for authenticated user"

        # Test getting user email
        email = auth_service.get_user_email(telegram_id)
        assert email == "test@example.com", f"Should return user email, got: {email}"

        # Test getting email for non-authenticated user
        auth_status_session.authenticated_users.remove(telegram_id)
        email = auth_service.get_user_email(telegram_id)
        assert email is None, "Should return None for non-authenticated user"

        print("✓ User authentication status test passed")

    finally:
        # Restore original function
        telegram_bot.auth.auth_service.get_db_session = original_get_db_session


if __name__ == "__main__":
    test_otp_generation()
    test_otp_hashing()
    test_email_validation()
    test_rate_limiting()
    test_send_otp_basic()
    test_otp_verification_system()
    test_authentication_persistence()
    test_user_authentication_status()
    print("\n🎉 All tests passed!")
