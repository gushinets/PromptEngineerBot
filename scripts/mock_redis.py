"""Mock redis module for testing without Redis dependency."""


class ConnectionPool:
    """Mock Redis connection pool."""

    @classmethod
    def from_url(cls, url, **kwargs):
        """Create a mock connection pool from URL."""
        return cls()


class Redis:
    """Mock Redis client."""

    def __init__(self, connection_pool=None):
        """Initialize mock Redis client."""

    def ping(self):
        """Mock ping command."""
        return True

    def hset(self, key, mapping):
        """Mock hset command."""
        return True

    def expire(self, key, ttl):
        """Mock expire command."""
        return True

    def hgetall(self, key):
        """Mock hgetall command."""
        return {}

    def hincrby(self, key, field, amount):
        """Mock hincrby command."""
        return 1

    def delete(self, key):
        """Mock delete command."""
        return 1

    def get(self, key):
        """Mock get command."""
        return

    def incr(self, key):
        """Mock incr command."""
        return 1

    def set(self, key, value, ex=None):
        """Mock set command."""
        return True

    def pipeline(self):
        """Mock pipeline command."""
        return MockPipeline()


class MockPipeline:
    """Mock Redis pipeline."""

    def hset(self, key, mapping):
        """Mock hset command in pipeline."""
        return self

    def expire(self, key, ttl):
        """Mock expire command in pipeline."""
        return self

    def incr(self, key):
        """Mock incr command in pipeline."""
        return self

    def set(self, key, value, ex=None):
        """Mock set command in pipeline."""
        return self

    def execute(self):
        """Mock execute command."""
        return [True, True, True]
