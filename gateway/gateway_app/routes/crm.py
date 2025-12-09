from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response

from gateway_app import main as gateway_main  # type: ignore

crm_router = APIRouter(prefix="/api/v1/crm")


@crm_router.api_route("/relationships{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_crm_relationships(path: str = "", request: Request = None) -> Response:  # type: ignore[assignment]
    if request is None:
        raise HTTPException(status_code=500, detail="Request context missing")
    headers = gateway_main._forward_headers(request)
    target_url = f"{gateway_main.CRM_SERVICE_URL}/crm/relationships{path}"
    return await gateway_main._proxy_request(request, target_url, headers)


@crm_router.api_route("/coach{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_crm_coach(path: str = "", request: Request = None) -> Response:  # type: ignore[assignment]
    if request is None:
        raise HTTPException(status_code=500, detail="Request context missing")
    headers = gateway_main._forward_headers(request)
    target_url = f"{gateway_main.CRM_SERVICE_URL}/crm/coach{path}"
    return await gateway_main._proxy_request(request, target_url, headers)


@crm_router.api_route("/analytics{path:path}", methods=["GET", "POST"])
async def proxy_crm_analytics(path: str = "", request: Request = None) -> Response:  # type: ignore[assignment]
    if request is None:
        raise HTTPException(status_code=500, detail="Request context missing")
    headers = gateway_main._forward_headers(request)
    target_url = f"{gateway_main.CRM_SERVICE_URL}/crm/analytics{path}"
    return await gateway_main._proxy_request(request, target_url, headers)


@crm_router.api_route("/billing{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_crm_billing(path: str = "", request: Request = None) -> Response:  # type: ignore[assignment]
    if request is None:
        raise HTTPException(status_code=500, detail="Request context missing")
    headers = gateway_main._forward_headers(request)
    target_url = f"{gateway_main.CRM_SERVICE_URL}/crm/billing{path}"
    return await gateway_main._proxy_request(request, target_url, headers)
