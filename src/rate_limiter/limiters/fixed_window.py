import time
import datetime
import threading
from rate_limiter.limiters import base
from rate_limiter.models import RateLimitRule,RateLimitKey,RateLimitResult
from rate_limiter.enums import RateLimitStatus

class FixedWindowLimiter(base.RateLimiter):
    
    
    def __init__(self,rule:RateLimitRule):
        super().__init__(rule)
        self._store = dict()
        self._lock = threading.Lock()
        
    def reset(self, key: RateLimitKey) -> None:
        with self._lock:
            self._store.pop(key.redis_key, None)         
            
    def is_allowed(self, key: RateLimitKey) -> RateLimitResult:
        curr_time = time.monotonic()
        with self._lock:
            
            redis_key = key.redis_key
            entry = self._store.get(redis_key)
            if entry is None:
                # key never seen before
                curr_count = 0
                window_start = curr_time
                self._store[redis_key] = {
                    "count": curr_count, 
                    "window_start_time": window_start
                }
            elif((curr_time - entry["window_start_time"]) > self.rule.window_seconds):
                # key exists but window has expired
                curr_count = 0
                window_start = curr_time
                self._store[redis_key] = {
                    "count": curr_count, 
                    "window_start_time": window_start
                }
            else:
                # key exists and window is still active
                curr_count = entry["count"]
                window_start = entry["window_start_time"]
            
            curr_count = curr_count + 1
            self._store[redis_key]={"count":curr_count, "window_start_time": window_start}
            
            reset_at = datetime.datetime.fromtimestamp(window_start+self.rule.window_seconds)
            
            remaining_req = max(0,self.rule.requests - curr_count)  #remaining req can go -ve in case when count is more than allowed number of request(the case where we need to drop)
            curr_status = None
            retry_after = None
            if(curr_count <= self.rule.requests):
                curr_status = RateLimitStatus.ALLOWED
                retry_after = 0.0
            else:
                curr_status = RateLimitStatus.DENIED
                retry_after = window_start+self.rule.window_seconds-curr_time

            return RateLimitResult(status=curr_status, limit=self.rule.requests, remaining = remaining_req,reset_at=reset_at, retry_after=retry_after)