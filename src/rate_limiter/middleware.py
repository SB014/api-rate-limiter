from starlette.middleware.base import BaseHTTPMiddleware 
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.types import ASGIApp
from rate_limiter.limiters.base import RateLimiter
from rate_limiter.enums import Scope
from rate_limiter.models import RateLimitKey

class RateLimitMiddleware(BaseHTTPMiddleware):
    
    def __init__(self, app: ASGIApp, limiter: RateLimiter, scope: Scope = Scope.IP, rule_name: str = "default"):
        super().__init__(app)
        self._limiter = limiter
        self._scope = scope
        self._rule_name = rule_name
    
    async def dispatch(self, request: Request, call_next) -> Response:
        
        client_ip = request.client.host if request.client else "unknown"
        
        # build RL key 
        rl_key = RateLimitKey(identifier=client_ip, scope=self._scope, rule_name=self._rule_name)
        
        # calling is_allowed of limiter
        
        rl_result = self._limiter.is_allowed(rl_key)
        if rl_result.is_allowed:
            response = await call_next(request)
            
            #Response headers in Starlette are a MutableHeaders object. You can update them like a dictionary:
                # for key, value in result.headers.items():
                #     response.headers[key] = value
                
            for key, value in rl_result.headers.items():
                response.headers[key] = value
            
            return response

        else:
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "retry_after": rl_result.retry_after},
                headers=dict(rl_result.headers)
            )
            