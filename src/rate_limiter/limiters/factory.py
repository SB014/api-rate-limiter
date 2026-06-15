from rate_limiter.enums import Algorithm
from rate_limiter.models import RateLimitRule
from rate_limiter.limiters.base import RateLimiter
from rate_limiter.limiters.async_fixed_window import AsyncFixedWindowLimiter
from rate_limiter.limiters.async_sliding_window import AsyncSlidingWindowLimiter
from rate_limiter.limiters.async_token_bucket import AsyncTokenBucketLimiter
from rate_limiter.exceptions import InvalidConfigurationError
        
class RateLimiterFactory:
    @staticmethod
    def create(algorithm: Algorithm, rule: RateLimitRule)->RateLimiter:
        if algorithm == Algorithm.FIXED_WINDOW:
            #no need to check by .value as algorithm inherits from str and Enum, so it can be compared directly
            return AsyncFixedWindowLimiter(rule)
        elif algorithm == Algorithm.SLIDING_WINDOW:
            return AsyncSlidingWindowLimiter(rule)
        elif algorithm == Algorithm.TOKEN_BUCKET:
            return AsyncTokenBucketLimiter(rule)
        else:
            raise InvalidConfigurationError (f"Unsupported algorithm: {algorithm}")