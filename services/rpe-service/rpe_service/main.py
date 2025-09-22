from .calculation import get_rpe_table as cached_rpe_table
from .rpe_calculations import get_volume, get_intensity, get_effort
from .calculation import round_to_step
from .schemas import RpeComputeRequest, RpeComputeResponse, ComputationError
from .rpc import get_effective_max
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict
import logging
from fastapi import APIRouter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="rpe-service", version="0.1.0")
# Регистрация роутов
router = APIRouter(prefix="/rpe")

@router.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}

@router.get("/table", tags=["Utils"])
def get_rpe_table() -> Dict[int, Dict[int, int]]:
    try:
        logger.info("Serving RPE table")
        return cached_rpe_table()
    except Exception as e:
        logger.error(f"RPE table error: {str(e)}")
        return JSONResponse(status_code=500, content=ComputationError(error="RPE_TABLE_ERROR", message=str(e)).model_dump())

@router.post("/compute", tags=["Utils"], response_model=RpeComputeResponse)
async def compute_rpe_set(payload: RpeComputeRequest) -> RpeComputeResponse:
    try:
        intensity = payload.intensity
        effort = payload.effort
        volume = payload.volume
        table = cached_rpe_table()
        max_weight = None
        if payload.user_max_id:
            try:
                effective_max = await get_effective_max(payload.user_max_id)
            except Exception as e:
                logger.error(f"Failed to get effective max: {str(e)}")
        elif payload.max_weight:
            max_weight = payload.max_weight
        provided = [p is not None for p in (intensity, effort, volume)]
        if sum(provided) >= 2:
            if intensity is not None and effort is not None and volume is None:
                volume = get_volume(table, intensity=intensity, effort=effort)
            elif volume is not None and effort is not None and intensity is None:
                intensity = get_intensity(table, volume=volume, effort=effort)
            elif volume is not None and intensity is not None and effort is None:
                effort = get_effort(table, volume=volume, intensity=intensity)
        weight = None
        if max_weight is not None and intensity is not None:
            raw = max_weight * (intensity / 100.0)
            weight = round_to_step(raw, payload.rounding_step, payload.rounding_mode)
        return RpeComputeResponse(intensity=intensity,effort=effort,volume=volume,weight=weight)
    except Exception as e:
        logger.error(f"Compute error: {str(e)}")
        return JSONResponse(status_code=400, content=ComputationError(error="COMPUTE_ERROR", message=str(e)).model_dump())

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

# Логирование зарегистрированных роутов
for route in app.routes:
    logger.info(f"Registered route: {route.path} ({route.methods})")
