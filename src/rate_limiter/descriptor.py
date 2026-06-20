from rate_limiter.limiters.base import RateLimiter
from rate_limiter.enums import Scope
import functools
import inspect
from rate_limiter.models import RateLimitKey
from rate_limiter.exceptions import RateLimitExceeded


class RateLimitDescriptor:
    """
    Descriptor-based alternative to the @rate_limit decorator, for use on
    class methods. Uses __get__ to bind the instance automatically — the
    same mechanism Python uses internally to bind `self` on regular methods.
    """

    def __init__(self, func, limiter: RateLimiter, scope: Scope = Scope.IP, rule_name: str = "default"):
        # config captured once at decoration time, stored as instance attributes
        # (closure cells in the function-based decorator version; here it's
        # plain object attributes — same idea, different storage mechanism)
        self._func = func
        self._limiter = limiter
        self._scope = scope
        self._rule_name = rule_name

        # update_wrapper is the class-based equivalent of @functools.wraps —
        # copies __name__, __doc__, __module__ etc from func onto self,
        # since self (not a plain function) is what replaces func here
        functools.update_wrapper(self, func)

    def __get__(self, instance, owner=None):
        # called by Python automatically whenever this descriptor is accessed
        # as a class attribute (e.g. api_handler.endpoint)
        if instance is None:
            # accessed from the class itself (ClassName.endpoint), not an instance
            # return the descriptor unchanged — no instance to bind
            return self

        # accessed from an instance (handler.endpoint) — bind that instance
        # as the first argument for when __call__ eventually runs, exactly
        # like Python automatically binds `self` for normal methods
        return functools.partial(self, instance)

    async def __call__(self, *args, **kwargs):
        # async because self._limiter.is_allowed is async (Phase 4 Redis limiters)
        # args[0] is the bound instance (from functools.partial in __get__)
        sig = inspect.signature(self._func)

        if "request" in sig.parameters:
            # maps raw *args/**kwargs to named parameters of the original function
            # so "request" can be found regardless of positional vs keyword call style
            bound = sig.bind(*args, **kwargs)
            request = str(bound.arguments.get("request"))

            # build the rate limit key from the extracted identifier
            rl_key = RateLimitKey(identifier=request, scope=self._scope, rule_name=self._rule_name)

            # await required — is_allowed is an async Redis call (Phase 4)
            rl_result = await self._limiter.is_allowed(rl_key)

            if rl_result.is_allowed:
                # call the real method — also awaited, since endpoint methods
                # in an async FastAPI app are themselves async def
                return await self._func(*args, **kwargs)

            raise RateLimitExceeded(
                "Rate Limit has exceeded",
                retry_after=rl_result.retry_after,
                limit=rl_result.limit
            )
        else:
            # no "request" parameter found — not rate limited, just pass through
            return await self._func(*args, **kwargs)


def rate_limit_descriptor(limiter: RateLimiter, scope: Scope = Scope.IP, rule_name: str = "default"):
    """
    Entry point — applied as @rate_limit_descriptor(limiter=...) on a class method.
    Wraps the decorated method in a RateLimitDescriptor instance.
    """
    def decorator(func):
        return RateLimitDescriptor(func, limiter, scope, rule_name)
    return decorator