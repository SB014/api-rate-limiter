from abc import ABC, abstractmethod
from rate_limiter.models import RateLimitResult,RateLimitRule,RateLimitKey

class RateLimiter(ABC):
    def __init__(self,rule:RateLimitRule):
        self.rule = rule
        
    @abstractmethod
    async def is_allowed(self, key: RateLimitKey)->RateLimitResult:
        """the core check"""
        ...
        
    @abstractmethod
    async def reset(self, key: RateLimitKey)->None:
        """clears state for a key"""
        ...
        

