import time
import datetime
import threading
from rate_limiter.limiters import base
from rate_limiter.models import RateLimitRule,RateLimitKey,RateLimitResult
from rate_limiter.enums import RateLimitStatus
from collections import deque
from typing import Dict

class SlidingWindowLimiter(base.RateLimiter):
    def __init__(self, rule: RateLimitRule):
        super().__init__(rule)
        self._store: Dict[str, deque] = dict()
        self._lock = threading.Lock()
        
    def reset(self, key: RateLimitKey) -> None:
        with self._lock:
            self._store.pop(key.redis_key, None)
    
    def is_allowed(self, key: RateLimitKey) -> RateLimitResult:
        curr_time = time.monotonic()
        with self._lock:
            redis_key = key.redis_key
            if redis_key not in self._store:
                self._store[redis_key] = deque()
                
            request_limit = self.rule.requests
            window_duration = self.rule.window_seconds
            
            timestamps_deque = self._store[redis_key]
            # removing expired timestamps from deque
            while timestamps_deque and timestamps_deque[0] < curr_time - window_duration:
                timestamps_deque.popleft()
               
            if(len(timestamps_deque) < request_limit):
                if(len(timestamps_deque)==0):
                    reset_at = datetime.datetime.fromtimestamp(curr_time+window_duration)
                else:
                    reset_at = datetime.datetime.fromtimestamp(timestamps_deque[0]+window_duration)                    
                curr_status = RateLimitStatus.ALLOWED
                timestamps_deque.append(curr_time)

                retry_after = 0.0
            else:
                curr_status = RateLimitStatus.DENIED
                reset_at = datetime.datetime.fromtimestamp(timestamps_deque[0]+window_duration)
                retry_after = timestamps_deque[0] + window_duration - curr_time
            
            remaining_req = max(0, request_limit-len(timestamps_deque))
            

        
            return RateLimitResult(status=curr_status, limit=self.rule.requests, remaining = remaining_req,reset_at=reset_at, retry_after=retry_after)
            
                