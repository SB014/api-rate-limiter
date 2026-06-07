import functools
from rate_limiter.limiters import RateLimiter
import inspect
from rate_limiter.enums import Scope
from rate_limiter.models import RateLimitKey
from rate_limiter.exceptions import RateLimitExceeded

def rate_limit(limiter: RateLimiter, scope: Scope = Scope.IP, rule_name: str = "default"):
    def decorator(func): 
        @functools.wraps(func)
        def wrapper(*args,**kwargs):
            sig = inspect.signature(func)
            if "request" in sig.parameters:
                
                #When the wrapper is called, it receives *args and **kwargs — raw positional and keyword arguments. It has no idea which argument is which by name, sig.bind(*args, **kwargs) takes those raw arguments and maps them to the parameter names of the original function. ex- args = (incoming_request,) kwargs = {"user_id": 42, "db": session}
                #bound.arguments = { "request": incoming_request,"user_id": 42,"db": session}
                
                bound = sig.bind(*args, **kwargs)
                request = str(bound.arguments.get("request"))
                
                #building a rate limit key
                
                rl_key = RateLimitKey(identifier=request, scope=scope, rule_name=rule_name)
                
                
                # calling is_allowed of limiter
                rl_result = limiter.is_allowed(rl_key)
                if rl_result.is_allowed:
                    return func(*args, **kwargs)
                
                raise RateLimitExceeded("Rate Limit has exceeded", retry_after=rl_result.retry_after, limit=rl_result.limit)
            else:
                return func(*args, **kwargs)
        return wrapper
    return decorator                
            

# call sign:
# @rate_limit(limiter=my_limiter)
# def my_endpoint(request):
#     ...


#rate_limit(limiter=my_limiter) runs first — it's just a regular function call that returns a decorator. Then that decorator receives my_endpoint.
