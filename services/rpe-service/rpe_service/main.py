from .calculation import get_rpe_table as cached_rpe_table
from .rpe_calculations import (
    get_volume,
    get_intensity,
    get_effort,
    IntensityNotFoundError,
    EffortNotFoundError,
    VolumeNotFoundError,
)
from .calculation import round_to_step
from .schemas import RpeComputeRequest, RpeComputeResponse, ComputationError
from .rpc import get_effective_max
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict
import logging
from fastapi import APIRouter, Header

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="rpe-service", version="0.1.0")
# Регистрация роутов
router = APIRouter(prefix="/rpe")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


def get_current_user_id(x_user_id: str | None = Header(default=None, alias="X-User-Id")) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header required")
    return x_user_id


@router.get("/health")
def health(user_id: str = Depends(get_current_user_id)) -> Dict[str, str]:
    return {"status": "ok"}


@router.get("/table", tags=["Utils"])
def get_rpe_table(user_id: str = Depends(get_current_user_id)) -> Dict[int, Dict[int, int]]:
    try:
        logger.info("Serving RPE table")
        return cached_rpe_table()
    except Exception as e:
        logger.error(f"RPE table error: {str(e)}")
        return JSONResponse(status_code=500, content=ComputationError(error="RPE_TABLE_ERROR", message=str(e)).model_dump())

@router.post("/compute", tags=["Utils"], response_model=RpeComputeResponse)
async def compute_rpe_set(
    payload: RpeComputeRequest,
    user_id: str = Depends(get_current_user_id),
) -> RpeComputeResponse:
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
            # Case 1: intensity + effort -> fill volume
            if intensity is not None and effort is not None and volume is None:
                try:
                    volume = get_volume(table, intensity=intensity, effort=effort)
                except (IntensityNotFoundError, EffortNotFoundError):
                    # Fallback: snap to nearest available intensity/effort for a valid volume
                    try:
                        # nearest intensity row
                        nearest_int = min(table.keys(), key=lambda x: abs(x - int(intensity)))
                        mapping = table[nearest_int]
                        # nearest effort key
                        nearest_eff = min(mapping.keys(), key=lambda k: abs(k - int(effort)))
                        volume = mapping[nearest_eff]
                        logger.warning(
                            "Adjusted (intensity,effort)->volume using nearest match | input=(%s,%s) -> intensity=%d effort=%d volume=%d",
                            str(intensity), str(effort), nearest_int, nearest_eff, volume
                        )
                        intensity = nearest_int
                        effort = nearest_eff
                    except Exception:
                        raise

            # Case 2: volume + effort -> fill intensity
            elif volume is not None and effort is not None and intensity is None:
                try:
                    intensity = get_intensity(table, volume=volume, effort=effort)
                except VolumeNotFoundError:
                    # Fallback: choose intensity row where reps at given effort is closest to volume
                    candidates = []
                    ekey = int(effort)
                    for i, mapping in table.items():
                        if ekey in mapping:
                            candidates.append((i, mapping[ekey]))
                    if candidates:
                        nearest_int, reps = min(candidates, key=lambda t: abs(t[1] - int(volume)))
                        intensity = nearest_int
                        volume = reps
                        logger.warning(
                            "Adjusted (volume,effort)->intensity using nearest match | requested_volume=%d effort=%d -> intensity=%d volume=%d",
                            volume, ekey, intensity, volume
                        )

            # Case 3: volume + intensity -> fill effort
            elif volume is not None and intensity is not None and effort is None:
                try:
                    effort = get_effort(table, volume=volume, intensity=intensity)
                except (IntensityNotFoundError, VolumeNotFoundError):
                    # Fallback: snap intensity to nearest row, then choose effort whose reps is closest to volume
                    nearest_int = min(table.keys(), key=lambda x: abs(x - int(intensity)))
                    mapping = table[nearest_int]
                    # pick effort whose reps is closest to requested volume
                    nearest_eff, reps = min(mapping.items(), key=lambda kv: abs(kv[1] - int(volume)))
                    logger.warning(
                        "Adjusted (intensity,volume)->effort using nearest match | input=(%s,%s) -> intensity=%d effort=%d volume=%d",
                        str(intensity), str(volume), nearest_int, nearest_eff, reps
                    )
                    intensity = nearest_int
                    effort = nearest_eff
                    volume = reps
        weight = None
        if max_weight is not None and intensity is not None:
            raw = max_weight * (intensity / 100.0)
            weight = round_to_step(raw, payload.rounding_step, payload.rounding_mode)
        return RpeComputeResponse(intensity=intensity,effort=effort,volume=volume,weight=weight)
    except Exception as e:
        error_msg = (
            f"RPE calculation failed: {str(e)}. "
            f"Input: intensity={payload.intensity}, volume={payload.volume}, effort={payload.effort}. "
            "This combination may not exist in the RPE table. "
            "Valid ranges: 90-100%→1-3 reps, 80-89%→3-6 reps, 70-79%→6-10 reps, 60-69%→10-20 reps, 50-59%→15-25 reps."
        )
        logger.error(error_msg)
        return JSONResponse(status_code=400, content=ComputationError(error="COMPUTE_ERROR", message=error_msg).model_dump())

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

# Логирование зарегистрированных роутов
for route in app.routes:
    logger.info(f"Registered route: {route.path} ({route.methods})")
