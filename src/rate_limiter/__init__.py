__version__ = "0.1.0"

from rate_limiter.enums import Algorithm, RateLimitStatus, Scope
from rate_limiter.models import RateLimitResult, RateLimitRule, RateLimitKey
from rate_limiter.exceptions import (
    RateLimiterError,
    RedisError,
    ConfigurationError,
    RedisConnectionError,
    RedisOperationError,
    InvalidConfigurationError,
    MissingConfigurationError,
    RateLimitExceeded,
    RateLimitIndeterminate,
    IdentifierMissingError,
    RuleNotFoundError,
)
from rate_limiter.config import Settings, get_settings

# Phase 2/4 — rate limiting algorithms and factory
from rate_limiter.limiters.base import RateLimiter
from rate_limiter.limiters.async_fixed_window import AsyncFixedWindowLimiter
from rate_limiter.limiters.async_sliding_window import AsyncSlidingWindowLimiter
from rate_limiter.limiters.async_token_bucket import AsyncTokenBucketLimiter
from rate_limiter.limiters.factory import RateLimiterFactory

# Phase 3 — application patterns for rate limiting
from rate_limiter.decorators import rate_limit
from rate_limiter.context import RateLimitContext
from rate_limiter.middleware import RateLimitMiddleware
from rate_limiter.descriptor import RateLimitDescriptor, rate_limit_descriptor

__all__ = [
    # enums
    "Algorithm",
    "RateLimitStatus",
    "Scope",
    # models
    "RateLimitResult",
    "RateLimitRule",
    "RateLimitKey",
    # exceptions
    "RateLimiterError",
    "RedisError",
    "ConfigurationError",
    "RedisConnectionError",
    "RedisOperationError",
    "InvalidConfigurationError",
    "MissingConfigurationError",
    "RateLimitExceeded",
    "RateLimitIndeterminate",
    "IdentifierMissingError",
    "RuleNotFoundError",
    # config
    "Settings",
    "get_settings",
    # limiters
    "RateLimiter",
    "AsyncFixedWindowLimiter",
    "AsyncSlidingWindowLimiter",
    "AsyncTokenBucketLimiter",
    "RateLimiterFactory",
    # application patterns
    "rate_limit",
    "RateLimitContext",
    "RateLimitMiddleware",
    "RateLimitDescriptor",
    "rate_limit_descriptor",
]