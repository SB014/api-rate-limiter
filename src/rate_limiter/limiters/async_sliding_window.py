from rate_limiter.limiters.redis_base import AsyncRedisRateLimiter
from rate_limiter.models import RateLimitKey, RateLimitResult
from rate_limiter.enums import RateLimitStatus
from datetime import datetime, timedelta
import time


class AsyncSlidingWindowLimiter(AsyncRedisRateLimiter):

    async def is_allowed(self, key: RateLimitKey) -> RateLimitResult:
        # get Redis connection from pool — reuses existing connection, no new TCP handshake
        redis = await self.get_redis()

        # Unix timestamp as float — must use time.time() not time.monotonic()
        # because Redis ZREMRANGEBYSCORE compares scores across calls and servers
        # time.monotonic() is relative to system boot — not universally comparable
        current_time = time.time()

        # remove all timestamps older than (now - window_seconds) from the sorted set
        # score range: 0 (beginning of time) to cutoff — anything outside the window
        # this is what makes it a SLIDING window — old entries are pruned on every request
        await redis.zremrangebyscore(key.redis_key, 0, current_time - self.rule.window_seconds)

        # count how many timestamps remain in the sorted set after pruning
        # zcard returns 0 for non-existent keys — no None check needed unlike redis.get()
        # this count = number of requests made within the current window
        count = await redis.zcard(key.redis_key)

        # remaining = how many more requests are allowed in this window
        # clamped to 0 — never goes negative
        remaining = max(0, self.rule.requests - count)

        # count < requests (not <=) because count is BEFORE adding current request
        # if count == requests, bucket is already full — deny the incoming request
        status = RateLimitStatus.ALLOWED if count < self.rule.requests else RateLimitStatus.DENIED

        # only add timestamp to sorted set if request is allowed
        # member = str(current_time) — unique string identifier for this request
        # score  = current_time      — float used for range-based expiry queries
        # denied requests are NOT logged — they don't consume quota
        if status == RateLimitStatus.ALLOWED:
            await redis.zadd(key.redis_key, {str(current_time): current_time})

        # reset TTL on every allowed request — keeps the key alive as long as
        # requests keep coming. Unlike fixed window where TTL is set ONCE,
        # sliding window resets TTL because the window slides with each request.
        # if user goes quiet for window_seconds, Redis auto-deletes the key.
        await redis.expire(key.redis_key, self.rule.window_seconds)

        # TTL was just set to window_seconds — no need for an extra redis.ttl() call
        ttl = self.rule.window_seconds

        limit = self.rule.requests
        reset_at = datetime.now() + timedelta(seconds=ttl)

        # retry_after: how long until the oldest request expires and frees a slot
        # only meaningful when denied — 0.0 when allowed
        retry_after = float(ttl) if status == RateLimitStatus.DENIED else 0.0

        return RateLimitResult(status, limit, remaining, reset_at, retry_after)

    async def reset(self, key: RateLimitKey) -> None:
        # delete the sorted set entirely — clears all timestamps for this key
        # used in tests (reset between cases) and admin API (manual reset)
        redis = await self.get_redis()
        await redis.delete(key.redis_key)