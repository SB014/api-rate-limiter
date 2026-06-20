from contextlib import asynccontextmanager
from fastapi import FastAPI
from rate_limiter.limiters.factory import RateLimiterFactory
from rate_limiter.models import RateLimitRule
from rate_limiter.config import get_settings
from rate_limiter.enums import Scope
from rate_limiter.middleware import RateLimitMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs once at server startup (before yield) and once at shutdown (after yield).
    This is where the single shared limiter instance is created — NOT inside
    get_redis() lazily, and NOT as a module-level global.

    Why here and not lazily in get_redis():
    If 100 simultaneous requests hit get_redis() when self._redis is None,
    all 100 could pass the None-check before any finishes creating the pool —
    each starts its own pool, wasting connections and silently overwriting
    self._redis. Creating it once here, before the server accepts any
    requests, eliminates that race entirely — there's no concurrent
    "first access" moment to race on.

    Why app.state and not a module-level global:
    app.state is scoped to this specific FastAPI instance. Tests can create
    a fresh FastAPI() app with its own isolated state — no shared global,
    no leakage between test runs or between multiple app instances in the
    same process.
    """
    # read configuration once at startup — cached via @lru_cache in get_settings()
    limiterConf = get_settings()

    # build the rule from settings — scope hardcoded to IP since Settings
    # doesn't currently expose a configurable scope field
    rule = RateLimitRule(
        requests=limiterConf.rate_limit.requests,
        window_seconds=limiterConf.rate_limit.window_seconds,
        algorithm=limiterConf.algorithm,
        scope=Scope.IP,
        burst=limiterConf.rate_limit.burst
    )

    # factory picks the correct concrete limiter class based on configured algorithm
    limiter = RateLimiterFactory.create(algorithm=limiterConf.algorithm, rule=rule)

    # stored on app.state — middleware reads this fresh on every request via
    # request.app.state.limiter (see middleware.py) rather than receiving it
    # at __init__ time, solving the chicken-and-egg ordering problem below
    app.state.limiter = limiter

    yield  # server runs and accepts requests here

    # cleanup on shutdown — closes the Redis connection pool gracefully
    # instead of leaking connections when the process exits
    await app.state.limiter.close()


app = FastAPI(title="Rate Limiter Gateway", lifespan=lifespan)

# middleware registered here — BEFORE lifespan has run, so the limiter
# does NOT exist yet at this exact line. This is fine because
# RateLimitMiddleware.dispatch() fetches request.app.state.limiter fresh
# on every request, not at __init__ time — by the time any real request
# arrives, lifespan has already completed and app.state.limiter is set.
app.add_middleware(RateLimitMiddleware)


@app.get("/health")
async def health_check():
    # simple liveness check — still passes through RateLimitMiddleware
    # since middleware wraps every request to the app, including this one
    return {"status": "ok"}