from __future__ import annotations

from fastapi import APIRouter, Request, Response

from gateway_app import main as gateway_main  # type: ignore

user_max_router = APIRouter(prefix="/api/v1/user-max")


@user_max_router.api_route("{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_user_max(request: Request, path: str = "") -> Response:
    target_url = f"{gateway_main.USER_MAX_SERVICE_URL}/user-max{path}"
    headers = gateway_main._forward_headers(request)
    return await gateway_main._proxy_request(request, target_url, headers)
