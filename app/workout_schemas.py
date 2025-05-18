from pydantic import BaseModel, Field
from typing import Optional, List, Union
from enum import Enum

class EffortType(str, Enum):
    RPE = "RPE"
    RIR = "RIR"

class WorkoutBase(BaseModel):
    name: str
    description: Optional[str] = None
    progression_template_id: Optional[int] = None

class WorkoutCreate(WorkoutBase):
    pass

class Workout(WorkoutBase):
    id: int

    class Config:
        from_attributes = True

class ExerciseListBase(BaseModel):
    name: str
    description: Optional[str] = None
    muscle_group: Optional[str] = None
    equipment: Optional[str] = None
    video_url: Optional[str] = None

class ExerciseListCreate(ExerciseListBase):
    pass

class ExerciseList(ExerciseListBase):
    id: int

    class Config:
        from_attributes = True

class ExerciseBase(BaseModel):
    name: str
    sets: int
    reps: int
    weight: int
    workout_id: int

class ExerciseCreate(ExerciseBase):
    pass

class Exercise(ExerciseBase):
    id: int

    class Config:
        from_attributes = True

class UserMaxBase(BaseModel):
    exercise_id: int
    max_weight: int
    rep_max: int

class UserMaxCreate(UserMaxBase):
    pass

class UserMax(UserMaxBase):
    id: int

    class Config:
        from_attributes = True

class ProgressionsBase(BaseModel):
    user_max_id: int
    sets: int
    intensity: int = Field(ge=1, le=100)
    effort: int = Field(ge=1, le=10)
    volume: int

class ProgressionsCreate(ProgressionsBase):
    pass

class Progressions(ProgressionsBase):
    id: int
    reps: Optional[Union[int, str]]
    calculated_weight: Optional[int]
    user_max_display: Optional[str]

    class Config:
        from_attributes = True

class ProgressionTemplateBase(BaseModel):
    user_max_id: int
    sets: int
    intensity: int = Field(ge=1, le=100)
    effort: int = Field(ge=1, le=10)
    volume: int

class ProgressionTemplateCreate(ProgressionTemplateBase):
    pass

class ProgressionTemplate(ProgressionTemplateBase):
    id: int

    class Config:
        from_attributes = True
