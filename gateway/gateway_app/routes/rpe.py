from __future__ import annotations

from fastapi import APIRouter, Request, Response

from gateway_app import main as gateway_main  # type: ignore

rpe_router = APIRouter(prefix="/api/v1/rpe")


@rpe_router.api_route("{path:path}", methods=["GET", "POST"])
async def proxy_rpe(request: Request, path: str = "") -> Response:
    target_url = f"{gateway_main.RPE_SERVICE_URL}/rpe{path}"
    headers = gateway_main._forward_headers(request)
    return await gateway_main._proxy_request(request, target_url, headers)
