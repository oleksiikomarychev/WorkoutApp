"""Social service routes."""

import httpx
import structlog
from fastapi import APIRouter, HTTPException, Request, Response, status

logger = structlog.get_logger(__name__)
social_router = APIRouter(prefix="/api/v1/social", tags=["social"])

# Social service URL
SOCIAL_SERVICE_URL = "http://social-service:8001"


@social_router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_social(
    path: str,
    request: Request
):
    """Proxy requests to Social Service."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user_id = user.get("uid")
    
    logger.info(f"Proxying to social service: {request.method} {path}, user_id={user_id}")
    
    # Add 'social/' prefix to path for social service
    full_path = f"social/{path}"
    
    # Read request body once (can only be consumed once in FastAPI)
    body = await request.body()
    
    # Log request body for POST requests to help debug
    if request.method == "POST":
        logger.info(f"POST request body: {body.decode('utf-8', errors='replace')}")
    
    try:
        async with httpx.AsyncClient() as client:
            # Prepare headers
            headers = dict(request.headers)
            headers.pop("host", None)  # Remove host header
            
            # Add user identification headers for social-service
            headers["X-User-Id"] = user_id
            
            logger.info(f"Making request to social-service: {request.method} {SOCIAL_SERVICE_URL}/{full_path}")
            
            # Make request to social service
            response = await client.request(
                method=request.method,
                url=f"{SOCIAL_SERVICE_URL}/{full_path}",
                headers=headers,
                params=request.query_params,
                content=body
            )
            
            logger.info(f"Social-service response: {response.status_code}, body: {response.content.decode('utf-8', errors='replace')[:500]}")
            
            # Return response
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
    except httpx.RequestError as e:
        logger.error(f"Error proxying to social service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Social service is temporarily unavailable"
        )
