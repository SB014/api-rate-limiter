from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.types import ASGIApp
from rate_limiter.enums import Scope
from rate_limiter.models import RateLimitKey


class RateLimitMiddleware(BaseHTTPMiddleware):

    def __init__(self, app: ASGIApp, scope: Scope = Scope.IP, rule_name: str = "default"):
        # limiter is NOT passed here anymore — it doesn't exist yet at registration time
        # add_middleware() runs BEFORE lifespan creates the limiter, so we can't accept it as a param
        # only scope and rule_name are needed at construction time — these don't depend on lifespan
        super().__init__(app)
        self._scope = scope
        self._rule_name = rule_name

    async def dispatch(self, request: Request, call_next) -> Response:

        # fetch the limiter from app.state on EVERY request, not once at construction
        # by the time any request arrives, lifespan has already run and set app.state.limiter
        # this breaks the chicken-and-egg problem: middleware registered before limiter exists,
        # but middleware only NEEDS the limiter when a real request comes in — which is always
        # after lifespan startup has completed
        limiter = request.app.state.limiter

        client_ip = request.client.host if request.client else "unknown"

        # build RL key using instance-level scope/rule_name (set once at registration)
        # combined with per-request client_ip
        rl_key = RateLimitKey(identifier=client_ip, scope=self._scope, rule_name=self._rule_name)

        # calling is_allowed of limiter — fetched fresh above, shared across all requests
        # since it's the SAME limiter object stored on app.state, all requests share state
        rl_result = await limiter.is_allowed(rl_key)

        if rl_result.is_allowed:
            response = await call_next(request)

            # Response headers in Starlette are a MutableHeaders object — update like a dict
            for key, value in rl_result.headers.items():
                response.headers[key] = value

            return response

        else:
            # request denied — route handler never runs, respond immediately with 429
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "retry_after": rl_result.retry_after},
                headers=dict(rl_result.headers)
            )