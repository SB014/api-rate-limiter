from rate_limiter.limiters.redis_base import AsyncRedisRateLimiter
from rate_limiter.models import RateLimitKey, RateLimitResult
from rate_limiter.enums import RateLimitStatus
from datetime import datetime, timedelta


class AsyncFixedWindowLimiter(AsyncRedisRateLimiter):

    async def is_allowed(self, key: RateLimitKey) -> RateLimitResult:
        # get Redis connection from pool — reuses existing connection, no new TCP handshake
        redis = await self.get_redis()

        # attempt to get current request count for this key
        # returns None if key doesn't exist (first request or window expired)
        # returns string if key exists — Redis stores all values as strings
        count = await redis.get(key.redis_key)

        if count is None:
            # first request OR previous window expired (Redis auto-deleted the key via TTL)
            # set counter to 1 and attach TTL equal to window_seconds
            # ex=window_seconds: key auto-deletes after window expires — no manual cleanup needed
            # TTL is set ONCE here and never reset — it represents the fixed window boundary
            await redis.set(key.redis_key, 1, ex=self.rule.window_seconds)
            count = 1
        else:
            # window is active — key exists, increment atomically
            # redis.incr is atomic — two simultaneous requests will always get sequential values
            # this replaces threading.Lock from Phase 2 — Redis single-threaded nature guarantees safety
            # incr returns the new value after incrementing — cast to int (Redis returns strings)
            count = int(await redis.incr(key.redis_key))

        # get remaining TTL in seconds — represents time until current window resets
        # redis.ttl returns -1 if key has no TTL, -2 if key doesn't exist
        # at this point key always exists so TTL is always positive
        ttl = await redis.ttl(key.redis_key)

        # count <= requests: ALLOWED (count includes current request)
        # count > requests: DENIED (window is exhausted)
        status = RateLimitStatus.ALLOWED if count <= self.rule.requests else RateLimitStatus.DENIED

        limit = self.rule.requests

        # remaining slots in current window — clamped to 0, never negative
        remaining = max(0, self.rule.requests - count)

        # reset_at: when the current window expires and counter resets
        # derived from TTL — time remaining until Redis auto-deletes the key
        reset_at = datetime.now() + timedelta(seconds=ttl)

        # retry_after: how long until the window resets and requests are accepted again
        # only meaningful when denied — 0.0 when allowed
        retry_after = float(ttl) if status == RateLimitStatus.DENIED else 0.0

        return RateLimitResult(status, limit, remaining, reset_at, retry_after)

    async def reset(self, key: RateLimitKey) -> None:
        # delete the counter key entirely — clears window state for this identifier
        # used in tests (reset between cases) and admin API (manual rate limit reset)
        redis = await self.get_redis()
        await redis.delete(key.redis_key)