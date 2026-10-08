"""Messaging service routes."""

import httpx
import structlog
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials

logger = structlog.get_logger(__name__)
messaging_router = APIRouter(prefix="/api/v1/messaging", tags=["messaging"])

# Messaging service URL
MESSAGING_SERVICE_URL = "http://messaging-service:8002"


@messaging_router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_messaging(
    path: str,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = None
):
    """Proxy requests to Messaging Service."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user_id = user.get("uid")
    
    logger.info(f"Proxying to messaging service: {request.method} {path}, user_id={user_id}")
    
    # Add 'messaging/' prefix to path for messaging service
    full_path = f"messaging/{path}"
    
    try:
        async with httpx.AsyncClient() as client:
            # Prepare headers
            headers = dict(request.headers)
            headers.pop("host", None)  # Remove host header
            
            # Make request to messaging service
            response = await client.request(
                method=request.method,
                url=f"{MESSAGING_SERVICE_URL}/{full_path}",
                headers=headers,
                params=request.query_params,
                content=await request.body()
            )
            
            # Return response
            return httpx.Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
    except httpx.RequestError as e:
        logger.error(f"Error proxying to messaging service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Messaging service is temporarily unavailable"
        )
