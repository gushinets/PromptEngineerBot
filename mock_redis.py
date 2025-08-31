"""Mock redis module for testing without Redis dependency."""


class ConnectionPool:
    @classmethod
    def from_url(cls, url, **kwargs):
        return cls()


class Redis:
    def __init__(self, connection_pool=None):
        pass

    def ping(self):
        return True

    def hset(self, key, mapping):
        return True

    def expire(self, key, ttl):
        return True

    def hgetall(self, key):
        return {}

    def hincrby(self, key, field, amount):
        return 1

    def delete(self, key):
        return 1

    def get(self, key):
        return None

    def incr(self, key):
        return 1

    def set(self, key, value, ex=None):
        return True

    def pipeline(self):
        return MockPipeline()


class MockPipeline:
    def hset(self, key, mapping):
        return self

    def expire(self, key, ttl):
        return self

    def incr(self, key):
        return self

    def set(self, key, value, ex=None):
        return self

    def execute(self):
        return [True, True, True]
