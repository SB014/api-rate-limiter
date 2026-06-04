from rate_limiter.enums import Algorithm
from rate_limiter.models import RateLimitRule
from rate_limiter.limiters.base import RateLimiter
from rate_limiter.limiters.fixed_window import FixedWindowLimiter
from rate_limiter.limiters.sliding_window import SlidingWindowLimiter
from rate_limiter.exceptions import InvalidConfigurationError
        
class RateLimiterFactory:
    @staticmethod
    def create(algorithm: Algorithm, rule: RateLimitRule)->RateLimiter:
        if algorithm == Algorithm.FIXED_WINDOW:
            #no need to check by .value as algorithm inherits from str and Enum, so it can be compared directly
            return FixedWindowLimiter(rule)
        elif algorithm == Algorithm.SLIDING_WINDOW:
            return SlidingWindowLimiter(rule)
        # TODO: elif algorithm == Algorithm.TOKEN_BUCKET:
        #     return TokenBucketLimiter(rule)
        else:
            raise InvalidConfigurationError (f"Unsupported algorithm: {algorithm}")