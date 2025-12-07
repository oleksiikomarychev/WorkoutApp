from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response

from gateway_app import main as gateway_main  # type: ignore

agent_router = APIRouter(prefix="/api/v1/agent")


@agent_router.post("/applied-plan-mass-edit")
async def proxy_agent_applied_plan_mass_edit(request: Request) -> Response:
    if gateway_main.AGENT_SERVICE_URL is None:
        raise HTTPException(status_code=503, detail="Agent service URL is not configured")

    headers = gateway_main._forward_headers(request)
    target_url = f"{gateway_main.AGENT_SERVICE_URL}/agent/applied-plan-mass-edit"
    return await gateway_main._proxy_request(request, target_url, headers)
