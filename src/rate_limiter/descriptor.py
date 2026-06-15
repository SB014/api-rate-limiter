from rate_limiter.limiters.base import RateLimiter
from rate_limiter.enums import Scope
import functools
import inspect
from rate_limiter.models import RateLimitKey
from rate_limiter.exceptions import RateLimitExceeded


class RateLimitDescriptor:
    
    def __init__(self, func, limiter:RateLimiter, scope: Scope = Scope.IP, rule_name: str = "default"):
        self._func = func
        self._limiter = limiter
        self._scope = scope
        self._rule_name = rule_name
        functools.update_wrapper(self, func)
    
    def __get__(self, instance, owner=None):
        if instance is None:
            return self     #accessed from class
        return functools.partial(self, instance)
    
    def __call__(self, *args, **kwargs):
        sig = inspect.signature(self._func)
        if "request" in sig.parameters:

            bound = sig.bind(*args, **kwargs)
            request = str(bound.arguments.get("request"))
            
            #building a rate limit key
            
            rl_key = RateLimitKey(identifier=request, scope=self._scope, rule_name=self._rule_name)
            
            
            # calling is_allowed of limiter
            rl_result = self._limiter.is_allowed(rl_key)
            if rl_result.is_allowed:
                return self._func(*args, **kwargs)
            
            raise RateLimitExceeded("Rate Limit has exceeded", retry_after=rl_result.retry_after, limit=rl_result.limit)
        else:
            return self._func(*args, **kwargs)
    
def rate_limit_descriptor(limiter: RateLimiter, scope=Scope.IP, rule_name="default"):
    def decorator(func):
        return RateLimitDescriptor(func, limiter, scope, rule_name)
    return decorator
