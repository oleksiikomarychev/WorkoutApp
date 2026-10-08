"""FastAPI HTTP service for RPE calculations."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging
import os

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import JSONResponse

from .calculation import calculate_rpe_set_values, get_rpe_table
from .config import settings
from .rpc import get_effective_max
from .schemas import (
    ComputationError,
    InternalPurgeResponse,
    RpeComputeRequest,
    RpeComputeResponse,
)

# Optional telemetry integrations (graceful fallback in test / dev environments)
try:
    from prometheus_fastapi_instrumentator import Instrumentator
except ImportError:
    Instrumentator = None  # type: ignore[assignment]

try:
    from sentry_sdk import set_tag, set_user
except ImportError:
    def set_tag(key: str, value: str) -> None:  # type: ignore[misc]
        pass

    def set_user(user: dict[str, str]) -> None:  # type: ignore[misc]
        pass

logger = logging.getLogger("rpe_service")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan events for startup preloading and graceful shutdown."""
    logger.info("Initializing RPE service...")
    try:
        get_rpe_table()
        logger.info("RPE table successfully preloaded on startup")
    except Exception as e:
        logger.warning("Could not preload RPE table on startup: %s", e)

    for route in app.routes:
        route_path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if route_path:
            logger.info("Registered route: %s (%s)", route_path, methods)

    yield
    logger.info("RPE service shut down cleanly")


app = FastAPI(
    title="rpe-service",
    version="0.1.0",
    description="Microservice for Rate of Perceived Exertion (RPE) calculation and weight suggestions",
    lifespan=lifespan,
)

if Instrumentator is not None:
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

router = APIRouter(prefix="/rpe")


@app.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    """Service health check endpoint."""
    return {"status": "ok"}


@app.post("/internal/users/{user_id}/purge", tags=["Internal"], response_model=InternalPurgeResponse)
def purge_user_internal(
    user_id: str,
    x_internal_secret: str | None = Header(default=None, alias="X-Internal-Secret"),
) -> InternalPurgeResponse:
    """Purge user data endpoint called during account deletion.

    RPE service is stateless and stores no persistent user data, but verifies
    the internal secret to integrate with the gateway purge pipeline.
    """
    expected_secret = (settings.INTERNAL_GATEWAY_SECRET or os.getenv("INTERNAL_GATEWAY_SECRET") or "").strip()
    if expected_secret and x_internal_secret != expected_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    logger.info("Purged user data for user_id=%s (stateless service, 0 records)", user_id)
    return InternalPurgeResponse(status="ok", deleted=0)


def get_current_user_id(x_user_id: str | None = Header(default=None, alias="X-User-Id")) -> str:
    """Dependency that extracts and validates the current user ID from headers."""
    if not x_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-User-Id header required")
    set_user({"id": str(x_user_id)})
    set_tag("service", "rpe-service")
    return x_user_id


@router.get("/table", tags=["Utils"])
def get_table(user_id: str = Depends(get_current_user_id)) -> dict[int, dict[int, int]] | JSONResponse:
    """Get the full RPE table matrix."""
    try:
        logger.info("Serving RPE table for user=%s", user_id)
        return get_rpe_table()
    except Exception as e:
        logger.error("RPE table error: %s", e)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ComputationError(error="RPE_TABLE_ERROR", message=str(e)).model_dump(),
        )


@router.post("/compute", tags=["Utils"], response_model=RpeComputeResponse)
async def compute_rpe_set(
    payload: RpeComputeRequest,
    user_id: str = Depends(get_current_user_id),
) -> RpeComputeResponse | JSONResponse:
    """Compute missing RPE parameters and calculated target weight."""
    try:
        max_weight = payload.max_weight
        if payload.user_max_id:
            try:
                fetched_max = await get_effective_max(payload.user_max_id, user_id=user_id)
                max_weight = fetched_max
            except Exception as e:
                logger.warning("Failed to get effective max for user_max_id=%s: %s", payload.user_max_id, e)

        table = get_rpe_table()
        intensity, effort, volume, weight = calculate_rpe_set_values(
            table=table,
            intensity=payload.intensity,
            effort=payload.effort,
            volume=payload.volume,
            max_weight=max_weight,
            rounding_step=payload.rounding_step,
            rounding_mode=payload.rounding_mode,
        )

        return RpeComputeResponse(
            intensity=intensity,
            effort=effort,
            volume=volume,
            weight=weight,
        )
    except Exception as e:
        error_msg = (
            f"RPE calculation failed: {str(e)}. "
            f"Input: intensity={payload.intensity}, volume={payload.volume}, effort={payload.effort}. "
            "This combination may not exist in the RPE table. "
            "Valid ranges: 90-100%→1-3 reps, 80-89%→3-6 reps, 70-79%→6-10 reps, 60-69%→10-20 reps, 50-59%→15-25 reps."
        )
        logger.error("%s", error_msg)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ComputationError(error="COMPUTE_ERROR", message=error_msg).model_dump(),
        )


app.include_router(router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=settings.SERVICE_PORT)

