from rate_limiter.limiters.base import RateLimiter
from rate_limiter.models import RateLimitResult,RateLimitKey
from rate_limiter.enums import RateLimitStatus
from datetime import datetime
import threading
import time
class TokenBucketLimiter(RateLimiter):
    
    def __init__(self,rule):
        super().__init__(rule)
        self._store: dict[str,dict] = {}
        self._lock = threading.Lock()
        self._refill_rate = self.rule.requests / self.rule.window_seconds
    
    
    def reset(self, key: RateLimitKey) -> None:
        with self._lock:
            self._store.pop(key.redis_key, None)  
        
    def is_allowed(self, key):
        curr_time = time.monotonic()
        with self._lock:
            redis_key = key.redis_key
            entry = self._store.get(redis_key)
            if entry is None:
                self._store[redis_key] = {"tokens": self.rule.requests, "last_refill": curr_time}
            else:
                #computing elapsed time since last refill
                elapsed_time = curr_time - entry["last_refill"]
                
                #computing the number of new tokens earned
                new_tokens = self._refill_rate * elapsed_time
                
                # capping the tokens to the maximum limit to prevent idle user accumulating unlimited tokens.
                
                max_tokens = self.rule.burst if self.rule.burst > 0 else self.rule.requests
                
                # add to current tokens keeping in mind the max token limit
                self._store[redis_key]["tokens"] = min(max_tokens,entry["tokens"] + new_tokens)
                
                # update last refill time
                self._store[redis_key]["last_refill"] = curr_time
            
            status = None
            retry_after = None
            remaining = None    
            if self._store[redis_key]["tokens"]>=1:
                status = RateLimitStatus.ALLOWED
                retry_after = 0.0
                remaining = max(0, int(self._store[redis_key]["tokens"] - 1))   #there may be fractional tokens as well
                
                # consume token
                self._store[redis_key]["tokens"] -= 1

            else:
                status = RateLimitStatus.DENIED
                
                # why are we doing 1 - tokens ? because if tokens is 0.5 then we need to wait for 0.5 time to get 1 token which is required to allow the request
                retry_after = (1 - self._store[redis_key]["tokens"]) / self._refill_rate
                remaining = int(self._store[redis_key]["tokens"])
            
            limit = self.rule.requests
            reset_at = datetime.fromtimestamp(curr_time + (1 / self._refill_rate))
            
            return RateLimitResult(status=status, limit=limit, remaining=remaining, reset_at=reset_at, retry_after=retry_after)