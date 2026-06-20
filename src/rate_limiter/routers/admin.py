from fastapi import APIRouter, Depends, Request
from rate_limiter.config import get_settings, Settings
from rate_limiter.models import RateLimitKey
from rate_limiter.enums import Scope

# prefix="/admin" means every route below is automatically namespaced —
# this route's full path becomes /admin/status, /admin/reset/{identifier}, etc.
# tags=["admin"] groups these routes together in the auto-generated OpenAPI docs
router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/status")
async def get_admin_status(settings: Settings = Depends(get_settings)):
    # Depends(get_settings) — FastAPI calls get_settings() and injects the result
    # get_settings is @lru_cache()'d, so this returns the same cached Settings
    # object on every call, not re-reading the .env file each time
    # GET is correct here — this is a read-only operation, no side effects
    return {
        "algorithm": settings.algorithm,
        "requests": settings.rate_limit.requests,
        "window_seconds": settings.rate_limit.window_seconds,
        "burst": settings.rate_limit.burst
    }


@router.post("/reset/{identifier}")
async def get_reset_identifier(identifier: str, request: Request):
    # identifier comes from the URL path, e.g. POST /admin/reset/192.168.1.1
    # request: Request is a built-in FastAPI type — automatically injected,
    # no Depends() needed, gives access to the current request and its app

    # POST (not GET) because this mutates state — resetting counts as a
    # side-effecting action, and GET requests should remain safe/idempotent
    # (browsers, proxies, crawlers can pre-fetch GET URLs unintentionally)
    rl_key = RateLimitKey(identifier=identifier, scope=Scope.IP)

    # limiter is NOT passed via Depends() — it's fetched directly from
    # request.app.state, which lifespan populated at server startup
    # (see gateway.py) — same pattern as RateLimitMiddleware uses
    await request.app.state.limiter.reset(rl_key)

    return {"message": f"Rate limit reset for {identifier}"}