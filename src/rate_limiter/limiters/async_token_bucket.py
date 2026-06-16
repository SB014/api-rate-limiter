from rate_limiter.limiters.redis_base import AsyncRedisRateLimiter
from rate_limiter.models import RateLimitKey, RateLimitResult, RateLimitRule
from rate_limiter.enums import RateLimitStatus
from datetime import datetime, timedelta
import time


class AsyncTokenBucketLimiter(AsyncRedisRateLimiter):

    def __init__(self, rule: RateLimitRule, redis_url: str = "redis://localhost:6379"):
        super().__init__(rule, redis_url)
        # pre-compute refill rate once — tokens earned per second
        # = requests / window_seconds (e.g. 100 req / 60s = 1.67 tokens/sec)
        # stored on self to avoid recalculating on every request
        self._refill_rate = self.rule.requests / self.rule.window_seconds

    async def is_allowed(self, key: RateLimitKey) -> RateLimitResult:
        # get Redis connection from pool — reuses existing connection, no new TCP handshake
        redis = await self.get_redis()

        # Unix timestamp as float — used for elapsed time calculation
        # time.time() not time.monotonic() — must be consistent across calls and servers
        curr_time = time.time()

        # retrieve existing bucket state — returns empty dict if key doesn't exist
        # hgetall returns all fields of a Redis hash as a dict of strings
        # empty dict = first request or bucket expired
        data = await redis.hgetall(key.redis_key)

        # safety initialisation — prevents UnboundLocalError if neither branch runs
        tokens = 0.0

        if not data:
            # first request — initialise bucket
            # consume 1 token immediately for this request (requests - 1 remaining)
            # no TTL set — token bucket has no fixed window, bucket persists indefinitely
            # idle users are naturally handled by the refill calculation on next request
            tokens = float(self.rule.requests)
            await redis.hset(key.redis_key, mapping={
                "token_count": tokens,
                "last_refill": curr_time
            })
            
        else:
            # bucket exists — refill tokens based on elapsed time since last request
            # elapsed_time: seconds since last refill
            elapsed_time = curr_time - float(data["last_refill"])

            # tokens earned since last request = elapsed_time * refill_rate
            # e.g. 2 seconds elapsed at 1.67 tokens/sec = 3.33 new tokens
            new_tokens = self._refill_rate * elapsed_time

            # cap tokens at burst size to prevent unlimited accumulation during idle periods
            # burst=0 means no burst configured — cap at rule.requests instead
            # e.g. burst=20: even after 1 hour idle, max 20 tokens available
            max_tokens = self.rule.burst if self.rule.burst > 0 else self.rule.requests

            # add earned tokens to current count, capped at max
            # cast data["token_count"] to float — Redis returns all values as strings
            tokens = min(max_tokens, float(data["token_count"]) + new_tokens)

            # persist updated token count and refill timestamp to Redis
            # last_refill updated to now — next request calculates elapsed from this moment
            await redis.hset(key.redis_key, mapping={
                "token_count": tokens,
                "last_refill": curr_time
            })

        if tokens >= 1:
            # sufficient tokens — allow request and consume one token
            status = RateLimitStatus.ALLOWED
            retry_after = 0.0

            # remaining = tokens after consuming 1, clamped to 0
            # int() truncates fractional tokens — you can't use half a token
            remaining = max(0, int(tokens - 1))

            # persist token consumption to Redis
            # write remaining (not tokens) — one token already consumed
            await redis.hset(key.redis_key, "token_count", remaining)

        else:
            # insufficient tokens — deny request
            # tokens < 1 means partial token available (e.g. 0.5)
            status = RateLimitStatus.DENIED

            # retry_after: time until enough tokens accumulate for 1 full token
            # (1 - tokens) = deficit (e.g. 1 - 0.5 = 0.5 tokens needed)
            # divide by refill_rate = seconds to earn that many tokens
            retry_after = (1 - tokens) / self._refill_rate

            # remaining = 0 (no full tokens available)
            # int(tokens) = 0 since tokens < 1
            remaining = int(tokens)

        limit = self.rule.requests

        # reset_at: when the next full token will be available
        # 1 / refill_rate = seconds to earn one token from zero
        # not perfectly accurate when tokens > 0 but sufficient for response headers
        reset_at = datetime.now() + timedelta(seconds=(1 / self._refill_rate))

        return RateLimitResult(
            status=status,
            limit=limit,
            remaining=remaining,
            reset_at=reset_at,
            retry_after=retry_after
        )

    async def reset(self, key: RateLimitKey) -> None:
        # delete the hash key entirely — clears token count and last_refill
        # next request will initialise a fresh bucket with full tokens
        # used in tests (reset between cases) and admin API (manual reset)
        redis = await self.get_redis()
        await redis.delete(key.redis_key)