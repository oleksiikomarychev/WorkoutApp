from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict, Optional

class WorkoutSet(BaseModel):
    exercise_id: int
    intensity: Optional[float] = None
    effort: Optional[float] = None
    volume: Optional[int] = None
    working_weight: Optional[float] = None

class ExerciseSet(BaseModel):
    exercise_id: int
    intensity: Optional[float] = None
    effort: Optional[float] = None
    volume: Optional[int] = None
    working_weight: Optional[float] = None

class ExerciseInWorkout(BaseModel):
    exercise_id: int
    sets: List[ExerciseSet]

class WorkoutExercise(BaseModel):
    exercise_id: int
    sets: List[WorkoutSet]

class WorkoutGenerationItem(BaseModel):
    name: str
    exercises: List[ExerciseInWorkout]
    # Optional fields for scheduled date and order index
    scheduled_for: Optional[str] = None
    plan_order_index: Optional[int] = None

class WorkoutGenerationRequest(BaseModel):
    applied_plan_id: int
    compute_weights: bool
    rounding_step: float
    rounding_mode: str
    workouts: List[WorkoutGenerationItem]

class WorkoutGenerationResponse(BaseModel):
    workout_ids: List[int]
    created_count: int | None = None
    existing_count: int | None = None
