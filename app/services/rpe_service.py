from typing import Optional, Tuple
from sqlalchemy.orm import Session
import math

from app.repositories.user_max_repository import UserMaxRepository
from app.workout_calculation import WorkoutCalculator
from app.schemas.rpe import RpeComputeRequest, RpeComputeResponse

class RpeService:
    def __init__(self, db: Session):
        self.db = db
        self.user_max_repo = UserMaxRepository(db)

    def _round_to_step(self, value: float, step: float, mode: str) -> float:
        if step <= 0:
            return value
        ratio = value / step
        if mode == 'floor':
            return math.floor(ratio) * step
        if mode == 'ceil':
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
                volume = WorkoutCalculator.get_volume(intensity=intensity, effort=effort)
            elif volume is not None and effort is not None and intensity is None:
                intensity = WorkoutCalculator.get_intensity(volume=volume, effort=effort)
            elif volume is not None and intensity is not None and effort is None:
                effort = WorkoutCalculator.get_effort(volume=volume, intensity=intensity)

        # Resolve max weight
        max_weight: Optional[float] = req.max_weight
        if max_weight is None and req.user_max_id is not None:
            user_max = self.user_max_repo.get_user_max(req.user_max_id)
            if user_max:
                max_weight = float(user_max.max_weight)

        # Compute working weight when possible
        weight: Optional[float] = None
        if max_weight is not None and intensity is not None:
            # Use true 1RM calculation instead of raw max_weight
            if req.user_max_id is not None:
                user_max = self.db.query(UserMax).filter(UserMax.id == req.user_max_id).first()
                if user_max:
                    true_1rm = WorkoutCalculator.get_true_1rm_from_user_max(user_max)
                    if true_1rm:
                        raw = true_1rm * (intensity / 100.0)
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
