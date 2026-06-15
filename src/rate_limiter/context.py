from rate_limiter.limiters.base import RateLimiter
from rate_limiter.models import RateLimitKey
from rate_limiter.exceptions import RateLimitExceeded

class RateLimitContext:
    
    def __init__(self, limiter:RateLimiter, key:RateLimitKey, reset_on_exit:bool = False):
        self._limiter = limiter
        self._key = key
        self._reset_on_exit = reset_on_exit
        self._result = None
    
    async def __aenter__(self):
        self._result = await self._limiter.is_allowed(self._key)
        if self._result.is_allowed:
            return self._result
        else:
            raise RateLimitExceeded(
                message=f"Rate limit exceeded for {self._key.identifier}. Retry after {self._result.retry_after:.1f} seconds.",
                retry_after=self._result.retry_after,
                limit=self._result.limit
)
        
    async def __aexit__(self, exc_type, exc, tb):
        # Returning True from __exit__ means suppress the exception - The with block would act as if nothing went wrong, even if RateLimitExceeded was raised inside __enter__ or inside the block body.
        # Returning False (what you have) means let the exception propagate — the caller sees it normally.
        if self._reset_on_exit:
            await self._limiter.reset(self._key)
        return False
        
    