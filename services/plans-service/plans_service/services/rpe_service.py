from typing import Optional
from sqlalchemy.orm import Session
import math
import os
import requests

from ..repositories.user_max_repository import UserMaxRepository
from ..workout_calculation import WorkoutCalculator
from ..schemas.rpe import RpeComputeRequest, RpeComputeResponse


class RpeService:
    def __init__(self, db: Session):
        self.db = db
        self.user_max_repo = UserMaxRepository(db)
        self.rpe_service_url = os.getenv("RPE_SERVICE_URL")

    def _round_to_step(self, value: float, step: float, mode: str) -> float:
        if step <= 0:
            return value
        ratio = value / step
        if mode == "floor":
            return math.floor(ratio) * step
        if mode == "ceil":
            return math.ceil(ratio) * step
        return round(ratio) * step

    def compute_set(self, req: RpeComputeRequest) -> RpeComputeResponse:
        intensity = req.intensity
        effort = req.effort
        volume = req.volume

        # Derive the missing parameter if exactly two provided
        provided = [p is not None for p in (intensity, effort, volume)]
        if sum(provided) >= 2:
            if intensity is not None and effort is not None and volume is None:
                volume = WorkoutCalculator.get_volume(
                    intensity=intensity, effort=effort
                )
            elif volume is not None and effort is not None and intensity is None:
                intensity = WorkoutCalculator.get_intensity(
                    volume=volume, effort=effort
                )
            elif volume is not None and intensity is not None and effort is None:
                effort = WorkoutCalculator.get_effort(
                    volume=volume, intensity=intensity
                )

        # Resolve max weight
        max_weight: Optional[float] = req.max_weight
        if max_weight is None and req.user_max_id is not None:
            user_max = self.user_max_repo.get_user_max(req.user_max_id)
            if user_max:
                max_weight = float(user_max.max_weight)

        # If external rpe-service is configured, delegate computation
        if self.rpe_service_url:
            try:
                true_1rm: Optional[float] = None
                if req.user_max_id is not None:
                    um = self.user_max_repo.get_user_max(req.user_max_id)
                    if um:
                        t1 = WorkoutCalculator.get_true_1rm_from_user_max(um)
                        true_1rm = float(t1) if t1 is not None else None

                payload = {
                    "intensity": intensity,
                    "effort": effort,
                    "volume": volume,
                    "max_weight": true_1rm if true_1rm is not None else max_weight,
                    "rounding_step": req.rounding_step,
                    "rounding_mode": req.rounding_mode,
                }
                resp = requests.post(
                    f"{self.rpe_service_url}/api/v1/rpe/compute",
                    json=payload,
                    timeout=5,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return RpeComputeResponse(
                        intensity=data.get("intensity"),
                        effort=data.get("effort"),
                        volume=data.get("volume"),
                        weight=data.get("weight"),
                    )
            except Exception:
                # Fallback to local computation on any error
                pass

        # Fallback: compute locally when service is unavailable or not configured
        weight: Optional[float] = None
        if max_weight is not None and intensity is not None:
            # Use true 1RM calculation instead of raw max_weight
            if req.user_max_id is not None:
                um = self.user_max_repo.get_user_max(req.user_max_id)
                if um:
                    true_1rm = WorkoutCalculator.get_true_1rm_from_user_max(um)
                    if true_1rm:
                        raw = float(true_1rm) * (intensity / 100.0)
                    else:
                        # Fallback to raw max_weight if calculation fails
                        raw = max_weight * (intensity / 100.0)
                else:
                    raw = max_weight * (intensity / 100.0)
            else:
                raw = max_weight * (intensity / 100.0)
            weight = self._round_to_step(raw, req.rounding_step, req.rounding_mode)

        return RpeComputeResponse(
            intensity=intensity,
            effort=effort,
            volume=volume,
            weight=weight,
        )
