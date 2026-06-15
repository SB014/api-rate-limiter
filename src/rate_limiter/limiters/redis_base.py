from rate_limiter.limiters.base import RateLimiter
from rate_limiter.models import RateLimitRule
import aioredis

class AsyncRedisRateLimiter(RateLimiter):
    def __init__(self, rule: RateLimitRule, redis_url: str = "redis://localhost:6379"):
        super().__init__(rule)
        self._redis_url = redis_url
        self._redis = None
        
    async def get_redis(self):
        if self._redis is None:
            self._redis = await aioredis.from_url(      # creates a connection pool automatically.
                url=self._redis_url,
                encoding = "utf-8",
                decode_responses = True                 # it ensures Redis returns strings instead of bytes.
            )
        return self._redis
    
    async def close(self):
        if self._redis:
            await self._redis.close()
            self._redis = None
            
            
# is_allowed and reset are abstract. AsyncRedisRateLimiter doesn't implement them — it's an intermediate base class. Python will raise TypeError if you try to instantiate it directly.
# This is intentional — AsyncRedisRateLimiter is not meant to be instantiated directly, only subclassed. But you need to be aware that Python will enforce this. 