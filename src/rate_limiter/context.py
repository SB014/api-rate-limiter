from rate_limiter.limiters.base import RateLimiter
from rate_limiter.models import RateLimitKey
from rate_limiter.exceptions import RateLimitExceeded

class RateLimitContext:
    
    def __init__(self, limiter:RateLimiter, key:RateLimitKey, reset_on_exit:bool = False):
        self._limiter = limiter
        self._key = key
        self._reset_on_exit = reset_on_exit
        self._result = None
    
    def __enter__(self):
        self._result = self._limiter.is_allowed(self._key)
        if self._result.is_allowed:
            return self._result
        else:
            raise RateLimitExceeded(
                message=f"Rate limit exceeded for {self._key.identifier}. Retry after {self._result.retry_after:.1f} seconds.",
                retry_after=self._result.retry_after,
                limit=self._result.limit
)
        
    def __exit__(self, exc_type, exc, tb):
        if self._reset_on_exit:
            self._limiter.reset(self._key)
        return False
        
    