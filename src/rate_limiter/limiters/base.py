from abc import ABC, abstractmethod
from rate_limiter.models import RateLimitResult,RateLimitRule,RateLimitKey

class RateLimiter(ABC):
    def __init__(self,rule:RateLimitRule):
        self.rule = rule
        
    @abstractmethod
    def is_allowed(self, key: RateLimitKey)->RateLimitResult:
        """the core check"""
        ...
        
    @abstractmethod
    def reset(self, key: RateLimitKey)->None:
        """clears state for a key"""
        ...
        

