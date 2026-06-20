from rate_limiter.limiters.base import RateLimiter
from rate_limiter.models import RateLimitRule
import aioredis


class AsyncRedisRateLimiter(RateLimiter):
    """
    Intermediate base class — shared Redis connection management for all
    Redis-backed limiters (fixed window, sliding window, token bucket).

    Does NOT implement is_allowed/reset — those remain abstract from RateLimiter.
    Cannot be instantiated directly: Python raises TypeError because the
    abstract methods are still unimplemented at this level. Only the three
    concrete subclasses (AsyncFixedWindowLimiter etc.) are meant to be used.
    """

    def __init__(self, rule: RateLimitRule, redis_url: str = "redis://localhost:6379"):
        super().__init__(rule)
        self._redis_url = redis_url
        # connection NOT created here — lazy initialisation
        # actual pool creation happens on first call to get_redis()
        self._redis = None

    async def get_redis(self):
        """
        Lazily creates and caches a Redis connection pool on first access.
        Subsequent calls reuse the same pool — avoids opening a new TCP
        connection on every single request, which would dominate latency
        at any meaningful request volume.

        NOTE: this lazy pattern has a known race condition if many concurrent
        requests hit get_redis() before self._redis is set — each would start
        its own pool creation. In this project, the race is avoided entirely
        because the gateway's FastAPI lifespan creates ONE limiter instance
        (and triggers its first get_redis() call) before the server starts
        accepting any requests — see gateway.py.
        """
        if self._redis is None:
            self._redis = await aioredis.from_url(
                url=self._redis_url,
                encoding="utf-8",
                decode_responses=True  # ensures Redis returns strings instead of bytes
            )
        return self._redis

    async def close(self):
        """
        Overrides RateLimiter.close() — actually performs cleanup here.
        Called from FastAPI's lifespan during shutdown (see gateway.py),
        ensuring the connection pool is released gracefully instead of
        leaking connections when the server stops.
        """
        if self._redis:
            await self._redis.close()
            self._redis = None