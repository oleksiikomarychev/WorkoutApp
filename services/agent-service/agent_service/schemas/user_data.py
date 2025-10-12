from pydantic import BaseModel
from typing import List, Optional, Dict

class UserDataInput(BaseModel):
    goals: List[str]
    available_equipment: List[str]
    workouts_per_microcycle: Optional[int] = None
    microcycles_per_mesocycle: Optional[int] = None
    mesocycles_per_plan: Optional[int] = None
    plan_duration_weeks: Optional[int] = None
    limits: Optional[Dict[str, float]] = None
    notes: Optional[str] = None
    current_metrics: Optional[Dict[str, float]] = None
    target_metrics: Optional[Dict[str, float]] = None
    normalization_unit: Optional[str] = None
    normalization_value: Optional[float] = None