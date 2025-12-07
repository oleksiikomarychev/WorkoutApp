from __future__ import annotations

from fastapi import APIRouter, Request, Response

from gateway_app import main as gateway_main  # type: ignore

sessions_router = APIRouter(prefix="/api/v1/sessions")


@sessions_router.api_route("{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_sessions(request: Request, path: str = "") -> Response:
    target_url = f"{gateway_main.WORKOUTS_SERVICE_URL}/workouts/sessions{path}"
    headers = gateway_main._forward_headers(request)
    return await gateway_main._proxy_request(request, target_url, headers)
