"""Tests for Redis client operations."""

import json
import time
from unittest.mock import Mock, patch

import pytest

from src.redis_client import RedisClient, get_redis_client, init_redis


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    with patch("src.redis_client.redis.Redis") as mock_redis_class:
        mock_client = Mock()
        mock_redis_class.return_value = mock_client

        # Mock pipeline
        mock_pipeline = Mock()
        mock_client.pipeline.return_value = mock_pipeline
        mock_pipeline.execute.return_value = [True, True, True]

        yield mock_client


@pytest.fixture
def redis_client_instance():
    """Create RedisClient instance for testing."""
    return RedisClient("redis://localhost:6379", max_connections=5)


class TestRedisClient:
    """Test RedisClient functionality."""

    def test_redis_client_initialization(self):
        """Test RedisClient initialization."""
        client = RedisClient("redis://localhost:6379", max_connections=5)

        assert client.redis_url == "redis://localhost:6379"
        assert client.max_connections == 5
        assert client._pool is None
        assert client._client is None

    def test_health_check_success(self, redis_client_instance, mock_redis):
        """Test successful Redis health check."""
        mock_redis.ping.return_value = True

        result = redis_client_instance.health_check()

        assert result is True
        mock_redis.ping.assert_called_once()

    def test_health_check_failure(self, redis_client_instance, mock_redis):
        """Test Redis health check failure."""
        mock_redis.ping.side_effect = Exception("Connection failed")

        result = redis_client_instance.health_check()

        assert result is False


class TestOTPStorage:
    """Test OTP storage operations."""

    def test_store_otp_success(self, redis_client_instance, mock_redis):
        """Test successful OTP storage."""
        mock_pipeline = mock_redis.pipeline.return_value

        result = redis_client_instance.store_otp(
            telegram_id=123456789,
            otp_hash="hashed_otp",
            email="test@example.com",
            ttl=300,
        )

        assert result is True
        mock_pipeline.hset.assert_called_once()
        mock_pipeline.expire.assert_called_once()
        mock_pipeline.execute.assert_called_once()

    def test_store_otp_with_original_complete_context(
        self, redis_client_instance, mock_redis
    ):
        """Test complete OTP context storage as per task 2.5 requirements."""
        mock_pipeline = mock_redis.pipeline.return_value

        result = redis_client_instance.store_otp_with_original(
            telegram_id=123456789,
            otp_hash="hashed_otp",
            email="test@example.com",
            email_original="Test@Example.Com",
            ttl=300,
        )

        assert result is True

        # Verify complete OTP context is stored with all required fields
        call_args = mock_pipeline.hset.call_args
        stored_data = call_args[1]["mapping"]

        # Verify all required fields from task 2.5: otp_hash, normalized_email, attempts, expires_at
        assert stored_data["otp_hash"] == "hashed_otp"
        assert (
            stored_data["normalized_email"] == "test@example.com"
        )  # Explicitly named as per design
        assert (
            stored_data["email_original"] == "Test@Example.Com"
        )  # Original format preserved
        assert stored_data["attempts"] == 0  # Attempt counter starts at 0
        assert "expires_at" in stored_data  # Expiry timestamp included

        mock_pipeline.hset.assert_called_once()
        mock_pipeline.expire.assert_called_once_with("otp:123456789", 300)
        mock_pipeline.execute.assert_called_once()

    def test_get_otp_data_success(self, redis_client_instance, mock_redis):
        """Test successful OTP data retrieval."""
        mock_otp_data = {
            b"otp_hash": b"hashed_otp",
            b"email": b"test@example.com",
            b"expires_at": str(int(time.time()) + 300).encode(),
            b"attempts": b"0",
        }
        mock_redis.hgetall.return_value = mock_otp_data

        result = redis_client_instance.get_otp_data(123456789)

        assert result is not None
        assert result["otp_hash"] == "hashed_otp"
        assert result["email"] == "test@example.com"
        assert result["attempts"] == 0
        assert isinstance(result["expires_at"], int)

    def test_get_otp_data_expired(self, redis_client_instance, mock_redis):
        """Test OTP data retrieval for expired OTP."""
        mock_otp_data = {
            b"otp_hash": b"hashed_otp",
            b"email": b"test@example.com",
            b"expires_at": str(int(time.time()) - 100).encode(),  # Expired
            b"attempts": b"0",
        }
        mock_redis.hgetall.return_value = mock_otp_data
        mock_redis.delete.return_value = 1

        result = redis_client_instance.get_otp_data(123456789)

        assert result is None
        mock_redis.delete.assert_called_once_with("otp:123456789")

    def test_get_otp_data_not_found(self, redis_client_instance, mock_redis):
        """Test OTP data retrieval when not found."""
        mock_redis.hgetall.return_value = {}

        result = redis_client_instance.get_otp_data(123456789)

        assert result is None

    def test_get_otp_data_complete_context(self, redis_client_instance, mock_redis):
        """Test OTP data retrieval with complete context as per task 2.5."""
        mock_otp_data = {
            b"otp_hash": b"hashed_otp",
            b"normalized_email": b"test@example.com",
            b"email_original": b"Test@Example.Com",
            b"expires_at": str(int(time.time()) + 300).encode(),
            b"attempts": b"1",
        }
        mock_redis.hgetall.return_value = mock_otp_data

        result = redis_client_instance.get_otp_data(123456789)

        assert result is not None
        # Verify all required fields are present and correctly parsed
        assert result["otp_hash"] == "hashed_otp"
        assert result["normalized_email"] == "test@example.com"
        assert result["email_original"] == "Test@Example.Com"
        assert result["attempts"] == 1
        assert isinstance(result["expires_at"], int)

    def test_attempt_boundaries_comprehensive(self, redis_client_instance, mock_redis):
        """Test comprehensive attempt boundaries handling."""
        # Test attempt 1
        mock_redis.exists.return_value = True
        mock_redis.hincrby.return_value = 1

        result = redis_client_instance.increment_otp_attempts(123456789)
        assert result == 1

        # Test attempt 2
        mock_redis.hincrby.return_value = 2
        result = redis_client_instance.increment_otp_attempts(123456789)
        assert result == 2

        # Test attempt 3 (at limit)
        mock_redis.hincrby.return_value = 3
        result = redis_client_instance.increment_otp_attempts(123456789)
        assert result == 3

        # Test attempt 4 (exceeds limit)
        mock_redis.hincrby.return_value = 4
        result = redis_client_instance.increment_otp_attempts(123456789)
        assert result == 4  # Should still increment but caller should handle deletion

    def test_expiry_handling_comprehensive(self, redis_client_instance, mock_redis):
        """Test comprehensive expiry handling and key cleanup."""
        # Test expired OTP with automatic cleanup
        expired_time = int(time.time()) - 100  # 100 seconds ago
        mock_otp_data = {
            b"otp_hash": b"hashed_otp",
            b"normalized_email": b"test@example.com",
            b"email_original": b"Test@Example.Com",
            b"expires_at": str(expired_time).encode(),
            b"attempts": b"2",
        }
        mock_redis.hgetall.return_value = mock_otp_data
        mock_redis.delete.return_value = 1

        result = redis_client_instance.get_otp_data(123456789)

        assert result is None  # Should return None for expired OTP
        mock_redis.delete.assert_called_once_with(
            "otp:123456789"
        )  # Should cleanup expired key

    def test_key_cleanup_scenarios(self, redis_client_instance, mock_redis):
        """Test various key cleanup scenarios as per task 2.5."""
        mock_redis.delete.return_value = 1

        # Test cleanup on successful verification
        result = redis_client_instance.delete_otp(123456789, "verification_success")
        assert result is True

        # Test cleanup after max attempts
        result = redis_client_instance.delete_otp(123456789, "max_attempts_reached")
        assert result is True

        # Test cleanup on expiry
        result = redis_client_instance.delete_otp(123456789, "expired")
        assert result is True

        # Verify all cleanup calls were made
        assert mock_redis.delete.call_count == 3

    def test_increment_otp_attempts_with_existence_check(
        self, redis_client_instance, mock_redis
    ):
        """Test OTP attempts increment with existence check as per task 2.5."""
        mock_redis.exists.return_value = True  # OTP key exists
        mock_redis.hincrby.return_value = 2

        result = redis_client_instance.increment_otp_attempts(123456789)

        assert result == 2
        mock_redis.exists.assert_called_once_with("otp:123456789")
        mock_redis.hincrby.assert_called_once_with("otp:123456789", "attempts", 1)

    def test_increment_otp_attempts_key_not_exists(
        self, redis_client_instance, mock_redis
    ):
        """Test OTP attempts increment when key doesn't exist."""
        mock_redis.exists.return_value = False  # OTP key doesn't exist

        result = redis_client_instance.increment_otp_attempts(123456789)

        assert result == -1  # Should return -1 when key doesn't exist
        mock_redis.exists.assert_called_once_with("otp:123456789")
        mock_redis.hincrby.assert_not_called()  # Should not increment if key doesn't exist

    def test_delete_otp_with_reason(self, redis_client_instance, mock_redis):
        """Test OTP deletion with reason logging as per task 2.5."""
        mock_redis.delete.return_value = 1

        result = redis_client_instance.delete_otp(123456789, "verification_success")

        assert result is True
        mock_redis.delete.assert_called_once_with("otp:123456789")

    def test_delete_otp_default_reason(self, redis_client_instance, mock_redis):
        """Test OTP deletion with default reason."""
        mock_redis.delete.return_value = 1

        result = redis_client_instance.delete_otp(123456789)

        assert result is True
        mock_redis.delete.assert_called_once_with("otp:123456789")

    def test_delete_otp_failure(self, redis_client_instance, mock_redis):
        """Test OTP deletion failure."""
        mock_redis.delete.return_value = 0  # Key didn't exist

        result = redis_client_instance.delete_otp(123456789, "cleanup")

        assert result is False
        mock_redis.delete.assert_called_once_with("otp:123456789")


class TestRateLimiting:
    """Test rate limiting operations."""

    def test_check_email_rate_limit_allowed(self, redis_client_instance, mock_redis):
        """Test email rate limit check when allowed."""
        mock_redis.get.return_value = b"2"  # Under limit of 3

        is_allowed, count = redis_client_instance.check_email_rate_limit(
            "test@example.com"
        )

        assert is_allowed is True
        assert count == 2
        mock_redis.get.assert_called_once_with("rl:email:test@example.com:hour")

    def test_check_email_rate_limit_exceeded(self, redis_client_instance, mock_redis):
        """Test email rate limit check when exceeded."""
        mock_redis.get.return_value = b"3"  # At limit of 3

        is_allowed, count = redis_client_instance.check_email_rate_limit(
            "test@example.com"
        )

        assert is_allowed is False
        assert count == 3

    def test_check_user_rate_limit_allowed(self, redis_client_instance, mock_redis):
        """Test user rate limit check when allowed."""
        mock_redis.get.return_value = b"4"  # Under limit of 5

        is_allowed, count = redis_client_instance.check_user_rate_limit(123456789)

        assert is_allowed is True
        assert count == 4
        mock_redis.get.assert_called_once_with("rl:tg:123456789:hour")

    def test_check_spacing_limit_allowed(self, redis_client_instance, mock_redis):
        """Test spacing limit check when allowed."""
        mock_redis.get.return_value = str(
            int(time.time()) - 120
        ).encode()  # 2 minutes ago

        is_allowed, seconds = redis_client_instance.check_spacing_limit(123456789)

        assert is_allowed is True
        assert seconds >= 60

    def test_check_spacing_limit_too_soon(self, redis_client_instance, mock_redis):
        """Test spacing limit check when too soon."""
        mock_redis.get.return_value = str(
            int(time.time()) - 30
        ).encode()  # 30 seconds ago

        is_allowed, seconds = redis_client_instance.check_spacing_limit(123456789)

        assert is_allowed is False
        assert seconds < 60

    def test_increment_rate_limits(self, redis_client_instance, mock_redis):
        """Test rate limit counter increments."""
        mock_pipeline = mock_redis.pipeline.return_value

        result = redis_client_instance.increment_rate_limits(
            123456789, "test@example.com"
        )

        assert result is True
        assert mock_pipeline.incr.call_count == 2  # Email and user counters
        assert mock_pipeline.expire.call_count == 2
        mock_pipeline.set.assert_called_once()  # Last send timestamp
        mock_pipeline.execute.assert_called_once()


class TestFlowState:
    """Test flow state management."""

    def test_set_flow_state(self, redis_client_instance, mock_redis):
        """Test setting flow state."""
        mock_redis.set.return_value = True

        result = redis_client_instance.set_flow_state(
            telegram_id=123456789,
            state="awaiting_email",
            data={"original_prompt": "test prompt"},
            ttl=86400,
        )

        assert result is True

        # Verify the data was serialized correctly
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "flow:123456789"

        stored_data = json.loads(call_args[0][1])
        assert stored_data["state"] == "awaiting_email"
        assert stored_data["original_prompt"] == "test prompt"

    def test_get_flow_state_success(self, redis_client_instance, mock_redis):
        """Test getting flow state."""
        flow_data = {
            "state": "awaiting_otp",
            "email": "test@example.com",
            "original_prompt": "test prompt",
        }
        mock_redis.get.return_value = json.dumps(flow_data)

        result = redis_client_instance.get_flow_state(123456789)

        assert result == flow_data
        mock_redis.get.assert_called_once_with("flow:123456789")

    def test_get_flow_state_not_found(self, redis_client_instance, mock_redis):
        """Test getting flow state when not found."""
        mock_redis.get.return_value = None

        result = redis_client_instance.get_flow_state(123456789)

        assert result is None

    def test_delete_flow_state(self, redis_client_instance, mock_redis):
        """Test deleting flow state."""
        mock_redis.delete.return_value = 1

        result = redis_client_instance.delete_flow_state(123456789)

        assert result is True
        mock_redis.delete.assert_called_once_with("flow:123456789")


class TestGlobalRedisClient:
    """Test global Redis client functions."""

    def test_init_redis(self):
        """Test Redis client initialization."""
        # Import and reload to avoid global mocks
        import importlib

        import src.redis_client

        importlib.reload(src.redis_client)

        # Only mock the underlying Redis connection
        with patch("src.redis_client.redis.Redis"):
            client = src.redis_client.init_redis("redis://localhost:6379")

            assert isinstance(client, src.redis_client.RedisClient)
            assert client.redis_url == "redis://localhost:6379"

    def test_get_redis_client(self):
        """Test getting Redis client."""
        # Initialize first
        original_client = init_redis("redis://localhost:6379")

        # Get client
        retrieved_client = get_redis_client()

        assert retrieved_client is original_client

        # Reset global state for other tests
        import src.redis_client

        src.redis_client.redis_client = None

    def test_get_redis_client_not_initialized(self):
        """Test getting Redis client when not initialized."""
        # Ensure global state is clean
        import src.redis_client

        src.redis_client.redis_client = None

        with pytest.raises(RuntimeError, match="Redis client not initialized"):
            get_redis_client()
