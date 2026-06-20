from abc import ABC, abstractmethod
from rate_limiter.models import RateLimitResult, RateLimitRule, RateLimitKey


class RateLimiter(ABC):
    """
    Abstract base class — the contract every rate limiting algorithm must follow.
    Enforces a common interface so the gateway, decorator, context manager, and
    factory can all work with any concrete limiter without knowing its internals.
    """

    def __init__(self, rule: RateLimitRule):
        # rule holds the configuration (requests, window_seconds, algorithm, burst)
        # shared by all subclasses — stored once here, never duplicated
        self.rule = rule

    @abstractmethod
    async def is_allowed(self, key: RateLimitKey) -> RateLimitResult:
        # async because Phase 4 implementations call Redis (I/O-bound operation)
        # Phase 2's in-memory limiters were sync — Redis-backed limiters require
        # await at every call site (middleware, decorator, context manager)
        # Python enforces at instantiation: any subclass missing this raises TypeError
        ...

    @abstractmethod
    async def reset(self, key: RateLimitKey) -> None:
        # clears state for a given key — used in tests and admin endpoints
        # async for the same reason as is_allowed — Redis DELETE is I/O-bound
        ...

    async def close(self) -> None:
        """
        Default no-op cleanup hook. Async Redis limiters override this to close
        their connection pool gracefully during FastAPI lifespan shutdown.

        Defined here (not abstract) so every limiter — even future non-Redis ones —
        can be called with `await limiter.close()` uniformly without type errors,
        whether or not it actually needs cleanup.
        """
        pass