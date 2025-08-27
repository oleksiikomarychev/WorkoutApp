from fastapi import APIRouter, Depends
from typing import Dict
from sqlalchemy.orm import Session
from ..config.prompts import RPE_TABLE
from ..dependencies import get_db
from ..services.rpe_service import RpeService
from ..schemas.rpe import RpeComputeRequest, RpeComputeResponse

router = APIRouter()

@router.get("/rpe", tags=["Utils"])
def get_rpe_table() -> Dict[int, Dict[int, int]]:
    """Return the RPE table: {intensity: {effort: reps}}"""
    return RPE_TABLE


@router.post("/rpe/compute", tags=["Utils"], response_model=RpeComputeResponse)
def compute_rpe_set(payload: RpeComputeRequest, db: Session = Depends(get_db)) -> RpeComputeResponse:
    """Compute missing set parameters and working weight from RPE table and user max.

    Provide any two of intensity (1-100), effort (1-10), volume (reps >=1).
    Optionally provide user_max_id or max_weight for weight calculation with rounding.
    """
    service = RpeService(db)
    return service.compute_set(payload)
