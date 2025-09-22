from pydantic import BaseModel
from typing import List, Optional

class ExerciseSetCreate(BaseModel):
    weight: Optional[float] = None
    volume: Optional[float] = None
    intensity: Optional[float] = None
    effort_type: Optional[str] = None
    effort: Optional[float] = None
    reps: Optional[int] = None

class ExerciseSet(BaseModel):
    id: int
    weight: Optional[float] = None
    volume: Optional[float] = None
    intensity: Optional[float] = None
    effort_type: Optional[str] = None
    effort: Optional[float] = None
    reps: Optional[int] = None

class ExerciseInstanceCreate(BaseModel):
    exercise_list_id: int
    sets: List[ExerciseSetCreate] = []
    notes: Optional[str] = None
    order: Optional[int] = None

class ExerciseInstanceResponse(BaseModel):
    id: int
    exercise_list_id: int
    sets: List[ExerciseSet] = []
    notes: Optional[str] = None
    order: Optional[int] = None
    workout_id: int
    user_max_id: Optional[int] = None
