from __future__ import annotations

import logging

import rpe_pb2 as rpe_pb2
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel

from gateway_app import main as gateway_main  # type: ignore
from gateway_app.grpc_clients import (
    create_user_context,
    grpc_client_manager,
)

logger = logging.getLogger(__name__)

rpe_router = APIRouter(prefix="/api/v1/rpe")


class RPEComputeRequest(BaseModel):
    intensity: float | None = None
    effort: float | None = None
    volume: int | None = None
    max_weight: float | None = None
    user_max_id: int | None = None
    rounding_step: float = 2.5
    rounding_mode: str = "nearest"


class RPEComputeResponse(BaseModel):
    intensity: float | None = None
    effort: float | None = None
    volume: int | None = None
    weight: float | None = None


def get_current_user_id(x_user_id: str | None = Header(default=None, alias="X-User-Id")) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header required")
    return x_user_id


@rpe_router.post("/compute", response_model=RPEComputeResponse)
async def compute_rpe(
    payload: RPEComputeRequest,
    user_id: str = Depends(get_current_user_id),
) -> RPEComputeResponse:
    """Compute RPE-based weight calculation using gRPC."""
    stub = await grpc_client_manager.get_rpe_stub()

    request = rpe_pb2.RPEComputeRequest(
        user_context=create_user_context(user_id),
        intensity=payload.intensity,
        effort=payload.effort,
        volume=payload.volume,
        max_weight=payload.max_weight,
        user_max_id=payload.user_max_id,
        rounding_step=payload.rounding_step,
        rounding_mode=payload.rounding_mode,
    )

    response = await stub.Compute(request)

    return RPEComputeResponse(
        weight=response.computed_weight,
    )


@rpe_router.get("/table")
async def get_rpe_table(request: Request) -> dict:
    """Get RPE table - still uses HTTP proxy for now."""
    # Check authentication from middleware first
    user = getattr(request.state, "user", None)
    if not user or not user.get("uid"):
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    # This endpoint doesn't have a gRPC equivalent yet, keep HTTP proxy
    target_url = f"{gateway_main.RPE_SERVICE_URL}/rpe/table"
    headers = gateway_main._forward_headers(request)
    return await gateway_main._proxy_request(request, target_url, headers)


@rpe_router.api_route("{path:path}", methods=["GET", "POST"])
async def proxy_rpe_fallback(request: Request, path: str = "") -> Response:
    """Fallback HTTP proxy for unimplemented gRPC endpoints."""
    target_url = f"{gateway_main.RPE_SERVICE_URL}/rpe{path}"
    headers = gateway_main._forward_headers(request)
    return await gateway_main._proxy_request(request, target_url, headers)
