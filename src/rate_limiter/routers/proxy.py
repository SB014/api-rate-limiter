from fastapi import APIRouter

router = APIRouter(prefix="/proxy", tags=["proxy"])


@router.get("/{path:path}")
async def proxy_passthrough(path: str):
    # placeholder demonstrating the gateway pattern — a real implementation
    # would use httpx.AsyncClient to forward this request to an actual
    # backend service and return its response. Kept minimal here since
    # the project's focus is the rate limiting layer, not a full reverse proxy.
    return {"message": f"Would forward request to backend service for path: {path}"}