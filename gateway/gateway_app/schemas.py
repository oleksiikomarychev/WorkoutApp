from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from .exercise_schemas import ExerciseInstanceCreate, ExerciseInstanceResponse

class WorkoutBase(BaseModel):
    name: str
    notes: Optional[str] = None
    status: Optional[str] = None
    started_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    rpe_session: Optional[int] = None
    location: Optional[str] = None
    readiness_score: Optional[int] = None
    applied_plan_id: Optional[int] = None
    plan_order_index: Optional[int] = None
    scheduled_for: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class WorkoutCreateWithExercises(WorkoutBase):
    #exercise_instances: List[ExerciseInstanceCreate] = []
    pass
class WorkoutResponse(WorkoutBase):
    id: int
    #exercise_instances: List[ExerciseInstanceCreate] = []

class WorkoutResponseWithExercises(WorkoutBase):
    id: int
    #exercise_instances: List[ExerciseInstanceResponse] = Field(..., alias="exercise_instances")


class MicrocycleCreate(BaseModel):
    name: str
    order_index: int
    normalization_value: Optional[float] = None
    normalization_unit: Optional[str] = None

class MesocycleCreate(BaseModel):
    name: str
    order_index: int
    microcycles: List[MicrocycleCreate]

class CalendarPlanCreate(BaseModel):
    name: str
    duration_weeks: int
    mesocycles: List[MesocycleCreate]
