from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
from .exercises import ExerciseInstance


class EffortType(str, Enum):
    RPE = "RPE"
    RIR = "RIR"


class WorkoutBase(BaseModel):
    name: str = Field(..., max_length=255)


class WorkoutCreate(WorkoutBase):
    # Optional metadata on creation
    notes: Optional[str] = None
    status: Optional[str] = None
    started_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    rpe_session: Optional[float] = None
    location: Optional[str] = None
    readiness_score: Optional[int] = None
    applied_plan_id: Optional[int] = None
    plan_order_index: Optional[int] = None
    scheduled_for: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class Workout(WorkoutBase):
    id: int
    exercise_instances: List["ExerciseInstance"] = []

    class Config:
        from_attributes = True
        json_encoders = {"datetime": lambda v: v.isoformat() if v else None}


class WorkoutUpdate(WorkoutBase):
    name: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None
    status: Optional[str] = None
    started_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    rpe_session: Optional[float] = None
    location: Optional[str] = None
    readiness_score: Optional[int] = None
    scheduled_for: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class WorkoutWithExercises(WorkoutBase):
    id: int
    exercise_instances: List["ExerciseInstance"]


class WorkoutResponse(WorkoutBase):
    id: int
    exercise_instances: List["ExerciseInstance"]
    applied_plan_id: Optional[int] = None
    plan_order_index: Optional[int] = None
    scheduled_for: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    started_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    rpe_session: Optional[float] = None
    location: Optional[str] = None
    readiness_score: Optional[int] = None

    class Config:
        from_attributes = True
        json_encoders = {"datetime": lambda v: v.isoformat() if v else None}


class WorkoutWithCalculatedWeight(WorkoutResponse):
    calculated_weight: Optional[float] = Field(None)


class WorkoutSummaryResponse(BaseModel):
    id: int
    name: str
    applied_plan_id: Optional[int] = None
    plan_order_index: Optional[int] = None
    scheduled_for: Optional[datetime] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True
        json_encoders = {"datetime": lambda v: v.isoformat() if v else None}


class WorkoutExerciseCreate(BaseModel):
    exercise_list_id: int
    sets: List[Dict[str, Any]] = Field(default_factory=list)
    notes: Optional[str] = None


class WorkoutExerciseUpdate(BaseModel):
    exercise_list_id: Optional[int] = None
    sets: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None
