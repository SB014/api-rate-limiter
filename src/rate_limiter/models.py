from __future__ import annotations
from dataclasses import field,dataclass
from datetime import datetime
from rate_limiter.enums import Algorithm,RateLimitStatus,Scope

@dataclass(frozen=True)
class RateLimitRule:
    requests : int
    window_seconds : int
    algorithm : Algorithm = Algorithm.TOKEN_BUCKET
    scope : Scope = Scope.IP
    burst : int = 0
    
    def __post_init__(self):
        if self.requests <= 0:
            raise ValueError(f"Requests value should be greater then zero | {self.requests}")
        if self.window_seconds <= 0:
            raise ValueError(f"window_seconds value should be greater then zero | {self.window_seconds}")
        if self.burst < 0:
            raise ValueError(f"Burst value cannot be negative | {self.burst}")

@dataclass(frozen=True)
class RateLimitKey:
    identifier: str
    scope : Scope
    rule_name : str = "default"
    
    @property
    def redis_key(self):
        scope_value = self.scope.value
        rule_name = self.rule_name
        identifier = self.identifier
        
        return f"rl:{self.scope.value}:{self.rule_name}:{self.identifier}"
    
@dataclass
class RateLimitResult:
    status : RateLimitStatus
    limit : int
    remaining : int
    reset_at : datetime
    retry_after : float = 0.0
    
    @property
    def is_allowed(self):
        return self.status == RateLimitStatus.ALLOWED
    
    @property
    def headers(self) -> dict[str, str]:
        return {"X-RateLimit-Limit" : str(self.limit), "X-RateLimit-Remaining" : str(self.remaining), "X-RateLimit-Reset" : str(self.reset_at.timestamp()), "Retry-After" : "0" if self.is_allowed else str(self.retry_after)} 
        