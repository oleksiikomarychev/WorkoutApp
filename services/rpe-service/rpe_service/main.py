from fastapi import FastAPI
from typing import Dict

from .calculation import RPE_TABLE, WorkoutCalculator
from .schemas import RpeComputeRequest, RpeComputeResponse

app = FastAPI(title="rpe-service", version="0.1.0")

@app.get("/api/v1/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}

@app.get("/api/v1/rpe", tags=["Utils"])
def get_rpe_table() -> Dict[int, Dict[int, int]]:
    """Return the RPE table: {intensity: {effort: reps}}"""
    return RPE_TABLE

@app.post("/api/v1/rpe/compute", tags=["Utils"], response_model=RpeComputeResponse)
def compute_rpe_set(payload: RpeComputeRequest) -> RpeComputeResponse:
    intensity = payload.intensity
    effort = payload.effort
    volume = payload.volume

    provided = [p is not None for p in (intensity, effort, volume)]
    if sum(provided) >= 2:
        if intensity is not None and effort is not None and volume is None:
            volume = WorkoutCalculator.get_volume(intensity=intensity, effort=effort)
        elif volume is not None and effort is not None and intensity is None:
            intensity = WorkoutCalculator.get_intensity(volume=volume, effort=effort)
        elif volume is not None and intensity is not None and effort is None:
            effort = WorkoutCalculator.get_effort(volume=volume, intensity=intensity)

    weight = None
    if payload.max_weight is not None and intensity is not None:
        raw = payload.max_weight * (intensity / 100.0)
        weight = WorkoutCalculator.round_to_step(raw, payload.rounding_step, payload.rounding_mode)

    return RpeComputeResponse(
        intensity=intensity,
        effort=effort,
        volume=volume,
        weight=weight,
    )
