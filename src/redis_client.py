"""
Redis client and operations for OTP storage, rate limiting, and flow state management.

This module provides Redis connection management, OTP storage with TTL,
rate limiting counters, and flow state operations.
"""

import json
import logging
import time
from typing import Any, Dict, Optional

import redis
from redis.connection import ConnectionPool

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client for OTP storage, rate limiting, and flow state management."""

    def __init__(self, redis_url: str, max_connections: int = 10):
        """
        Initialize Redis client with connection pooling.

        Args:
            redis_url: Redis connection URL
            max_connections: Maximum connections in pool
        """
        self.redis_url = redis_url
        self.max_connections = max_connections
        self._pool = None
        self._client = None

    def get_client(self) -> redis.Redis:
        """Get or create Redis client with connection pooling."""
        if self._client is None:
            self._pool = ConnectionPool.from_url(
                self.redis_url,
                max_connections=self.max_connections,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
            )
            self._client = redis.Redis(connection_pool=self._pool)
        return self._client

    def health_check(self) -> bool:
        """
        Check Redis connectivity.

        Returns:
            True if Redis is healthy, False otherwise
        """
        try:
            client = self.get_client()
            client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

    # OTP Storage Operations

    def store_otp(
        self, telegram_id: int, otp_hash: str, email: str, ttl: int = 300
    ) -> bool:
        """
        Store OTP hash with metadata in Redis.

        Args:
            telegram_id: User's Telegram ID
            otp_hash: Hashed OTP value
            email: Normalized email address
            ttl: Time to live in seconds (default 5 minutes)

        Returns:
            True if stored successfully, False otherwise
        """
        try:
            client = self.get_client()
            key = f"otp:{telegram_id}"

            otp_data = {
                "otp_hash": otp_hash,
                "email": email,
                "expires_at": int(time.time()) + ttl,
                "attempts": 0,
            }

            # Store as hash with TTL
            pipe = client.pipeline()
            pipe.hset(key, mapping=otp_data)
            pipe.expire(key, ttl)
            pipe.execute()

            logger.debug(
                f"OTP hash stored for telegram_id {telegram_id}, expires in {ttl}s"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to store OTP for telegram_id {telegram_id}: {e}")
            return False

    def store_otp_with_original(
        self,
        telegram_id: int,
        otp_hash: str,
        email: str,
        email_original: str,
        ttl: int = 300,
    ) -> bool:
        """
        Store complete OTP context in Redis with all required fields.

        Args:
            telegram_id: User's Telegram ID
            otp_hash: Hashed OTP value
            email: Normalized email address
            email_original: Original email address as entered by user
            ttl: Time to live in seconds (default 5 minutes)

        Returns:
            True if stored successfully, False otherwise
        """
        try:
            client = self.get_client()
            key = f"otp:{telegram_id}"

            # Store complete OTP context as required by task 2.5
            otp_data = {
                "otp_hash": otp_hash,
                "normalized_email": email,  # Explicitly named as per design
                "email_original": email_original,
                "expires_at": int(time.time()) + ttl,
                "attempts": 0,
            }

            # Store as hash with TTL
            pipe = client.pipeline()
            pipe.hset(key, mapping=otp_data)
            pipe.expire(key, ttl)
            pipe.execute()

            logger.debug(
                f"Complete OTP context stored for telegram_id {telegram_id}, expires in {ttl}s"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to store OTP for telegram_id {telegram_id}: {e}")
            return False

    def get_otp_data(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve OTP data from Redis.

        Args:
            telegram_id: User's Telegram ID

        Returns:
            OTP data dict or None if not found/expired
        """
        try:
            client = self.get_client()
            key = f"otp:{telegram_id}"

            otp_data = client.hgetall(key)
            if not otp_data:
                return None

            # Convert bytes to strings and parse
            parsed_data = {}
            for k, v in otp_data.items():
                key_str = k.decode("utf-8") if isinstance(k, bytes) else k
                val_str = v.decode("utf-8") if isinstance(v, bytes) else v

                if key_str in ["expires_at", "attempts"]:
                    parsed_data[key_str] = int(val_str)
                else:
                    parsed_data[key_str] = val_str

            # Check if expired
            if parsed_data.get("expires_at", 0) < time.time():
                self.delete_otp(telegram_id)
                return None

            return parsed_data

        except Exception as e:
            logger.error(f"Failed to get OTP data for telegram_id {telegram_id}: {e}")
            return None

    def increment_otp_attempts(self, telegram_id: int) -> int:
        """
        Increment OTP verification attempts counter and persist on every verification attempt.

        Args:
            telegram_id: User's Telegram ID

        Returns:
            New attempt count, or -1 if error
        """
        try:
            client = self.get_client()
            key = f"otp:{telegram_id}"

            # Check if OTP exists before incrementing
            if not client.exists(key):
                logger.warning(f"OTP key does not exist for telegram_id {telegram_id}")
                return -1

            # Increment attempt counter atomically
            new_count = client.hincrby(key, "attempts", 1)

            # Log the attempt increment for audit purposes
            logger.debug(
                f"OTP attempts incremented to {new_count} for telegram_id {telegram_id}"
            )

            return new_count

        except Exception as e:
            logger.error(
                f"Failed to increment OTP attempts for telegram_id {telegram_id}: {e}"
            )
            return -1

    def delete_otp(self, telegram_id: int, reason: str = "cleanup") -> bool:
        """
        Delete OTP key after >3 failed attempts or on successful verification.

        Args:
            telegram_id: User's Telegram ID
            reason: Reason for deletion (for logging)

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            client = self.get_client()
            key = f"otp:{telegram_id}"

            result = client.delete(key)
            logger.debug(
                f"OTP key deleted for telegram_id {telegram_id}, reason: {reason}"
            )
            return result > 0

        except Exception as e:
            logger.error(f"Failed to delete OTP for telegram_id {telegram_id}: {e}")
            return False

    # Rate Limiting Operations

    def check_email_rate_limit(
        self, email: str, limit: int = 3, window: int = 3600
    ) -> tuple[bool, int]:
        """
        Check email-based rate limiting.

        Args:
            email: Normalized email address
            limit: Maximum sends per window (default 3)
            window: Time window in seconds (default 1 hour)

        Returns:
            Tuple of (is_allowed, current_count)
        """
        try:
            client = self.get_client()
            key = f"rl:email:{email}:hour"

            current_count = client.get(key)
            current_count = int(current_count) if current_count else 0

            is_allowed = current_count < limit
            logger.debug(
                f"Email rate limit check for {email}: {current_count}/{limit}, allowed={is_allowed}"
            )

            return is_allowed, current_count

        except Exception as e:
            logger.error(f"Failed to check email rate limit for {email}: {e}")
            return False, 0

    def check_user_rate_limit(
        self, telegram_id: int, limit: int = 5, window: int = 3600
    ) -> tuple[bool, int]:
        """
        Check user-based rate limiting.

        Args:
            telegram_id: User's Telegram ID
            limit: Maximum sends per window (default 5)
            window: Time window in seconds (default 1 hour)

        Returns:
            Tuple of (is_allowed, current_count)
        """
        try:
            client = self.get_client()
            key = f"rl:tg:{telegram_id}:hour"

            current_count = client.get(key)
            current_count = int(current_count) if current_count else 0

            is_allowed = current_count < limit
            logger.debug(
                f"User rate limit check for telegram_id {telegram_id}: {current_count}/{limit}, allowed={is_allowed}"
            )

            return is_allowed, current_count

        except Exception as e:
            logger.error(
                f"Failed to check user rate limit for telegram_id {telegram_id}: {e}"
            )
            return False, 0

    def check_spacing_limit(
        self, telegram_id: int, min_spacing: int = 60
    ) -> tuple[bool, int]:
        """
        Check minimum spacing between OTP sends.

        Args:
            telegram_id: User's Telegram ID
            min_spacing: Minimum seconds between sends (default 60)

        Returns:
            Tuple of (is_allowed, seconds_since_last)
        """
        try:
            client = self.get_client()
            key = f"rl:tg:{telegram_id}:last"

            last_send = client.get(key)
            if not last_send:
                return True, min_spacing  # No previous send

            last_send_time = int(last_send)
            current_time = int(time.time())
            seconds_since_last = current_time - last_send_time

            is_allowed = seconds_since_last >= min_spacing
            logger.debug(
                f"Spacing check for telegram_id {telegram_id}: {seconds_since_last}s since last, allowed={is_allowed}"
            )

            return is_allowed, seconds_since_last

        except Exception as e:
            logger.error(
                f"Failed to check spacing limit for telegram_id {telegram_id}: {e}"
            )
            return False, 0

    def increment_rate_limits(
        self, telegram_id: int, email: str, window: int = 3600
    ) -> bool:
        """
        Increment rate limiting counters after successful OTP send.

        Args:
            telegram_id: User's Telegram ID
            email: Normalized email address
            window: Time window in seconds (default 1 hour)

        Returns:
            True if incremented successfully, False otherwise
        """
        try:
            client = self.get_client()
            current_time = int(time.time())

            # Use pipeline for atomic operations
            pipe = client.pipeline()

            # Increment email counter
            email_key = f"rl:email:{email}:hour"
            pipe.incr(email_key)
            pipe.expire(email_key, window)

            # Increment user counter
            user_key = f"rl:tg:{telegram_id}:hour"
            pipe.incr(user_key)
            pipe.expire(user_key, window)

            # Update last send timestamp
            last_key = f"rl:tg:{telegram_id}:last"
            pipe.set(last_key, current_time, ex=window)

            pipe.execute()

            logger.debug(
                f"Rate limit counters incremented for telegram_id {telegram_id}, email {email}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to increment rate limits for telegram_id {telegram_id}: {e}"
            )
            return False

    # Flow State Management

    def set_flow_state(
        self, telegram_id: int, state: str, data: Dict[str, Any], ttl: int = 86400
    ) -> bool:
        """
        Set user flow state in Redis.

        Args:
            telegram_id: User's Telegram ID
            state: Flow state name
            data: State data dictionary
            ttl: Time to live in seconds (default 24 hours)

        Returns:
            True if set successfully, False otherwise
        """
        try:
            client = self.get_client()
            key = f"flow:{telegram_id}"

            flow_data = {"state": state, **data}

            client.set(key, json.dumps(flow_data), ex=ttl)
            logger.debug(f"Flow state '{state}' set for telegram_id {telegram_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to set flow state for telegram_id {telegram_id}: {e}")
            return False

    def get_flow_state(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user flow state from Redis.

        Args:
            telegram_id: User's Telegram ID

        Returns:
            Flow state data or None if not found
        """
        try:
            client = self.get_client()
            key = f"flow:{telegram_id}"

            flow_data = client.get(key)
            if not flow_data:
                return None

            return json.loads(flow_data)

        except Exception as e:
            logger.error(f"Failed to get flow state for telegram_id {telegram_id}: {e}")
            return None

    def delete_flow_state(self, telegram_id: int) -> bool:
        """
        Delete user flow state from Redis.

        Args:
            telegram_id: User's Telegram ID

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            client = self.get_client()
            key = f"flow:{telegram_id}"

            result = client.delete(key)
            logger.debug(f"Flow state deleted for telegram_id {telegram_id}")
            return result > 0

        except Exception as e:
            logger.error(
                f"Failed to delete flow state for telegram_id {telegram_id}: {e}"
            )
            return False


# Global Redis client instance
redis_client: Optional[RedisClient] = None


def init_redis(redis_url: str, max_connections: int = 10) -> RedisClient:
    """
    Initialize global Redis client.

    Args:
        redis_url: Redis connection URL
        max_connections: Maximum connections in pool

    Returns:
        RedisClient instance
    """
    global redis_client
    redis_client = RedisClient(redis_url, max_connections)
    return redis_client


def get_redis_client() -> RedisClient:
    """
    Get the global Redis client instance.

    Returns:
        RedisClient instance

    Raises:
        RuntimeError: If Redis client is not initialized
    """
    if redis_client is None:
        raise RuntimeError("Redis client not initialized. Call init_redis() first.")
    return redis_client


def init_redis_client(config) -> RedisClient:
    """
    Initialize Redis client from configuration.

    Args:
        config: BotConfig instance with Redis settings

    Returns:
        RedisClient instance
    """
    return init_redis(config.redis_url, config.redis_max_connections)
