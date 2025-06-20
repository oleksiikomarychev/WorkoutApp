from pydantic import BaseModel, Field, validator, HttpUrl
from typing import Optional, List, Union, Dict, Any
from enum import Enum
from datetime import datetime

class EffortType(str, Enum):
    RPE = "RPE"
    RIR = "RIR"


class WorkoutBase(BaseModel):
    name: str = Field(..., max_length=255)
    progression_template_id: Optional[int] = None

class WorkoutCreate(WorkoutBase):
    pass

class Workout(WorkoutBase):
    id: int
    exercise_instances: List['ExerciseInstance'] = []

    class Config:
        from_attributes = True

class ExerciseListBase(BaseModel):
    name: str = Field(..., max_length=255)
    muscle_group: Optional[str] = Field(None)
    equipment: Optional[str] = Field(None)

class ExerciseListCreate(ExerciseListBase):
    pass

class ExerciseList(ExerciseListBase):
    id: int

    class Config:
        from_attributes = True

class ExerciseBase(BaseModel):
    name: str = Field(..., max_length=255)
    exercise_definition_id: Optional[int] = None
    
    class Config:
        from_attributes = True

class ExerciseCreate(ExerciseBase):
    pass

class Exercise(ExerciseBase):
    id: int
    instances: List['ExerciseInstance'] = []


class ExerciseInstanceBase(BaseModel):
    exercise_id: int = Field(...)
    workout_id: int = Field(...)
    volume: int = Field(..., ge=1)
    intensity: int = Field(..., ge=1, le=100)
    effort: int = Field(..., ge=1, le=10)
    weight: int = Field(0, ge=0)
    notes: Optional[str] = None
    
    class Config:
        from_attributes = True

class ExerciseInstanceCreate(ExerciseInstanceBase):
    pass

class ExerciseInstance(ExerciseInstanceBase):
    id: int
    exercise: Optional[Exercise] = None

    class Config:
        from_attributes = True

class UserMaxBase(BaseModel):
    exercise_id: int = Field(...)
    max_weight: int = Field(..., gt=0)
    rep_max: int = Field(..., ge=1, le=20)

class UserMaxCreate(UserMaxBase):
    pass


class UserMaxUpdate(BaseModel):
    exercise_id: Optional[int] = Field(None)
    max_weight: Optional[int] = Field(None, gt=0)
    rep_max: Optional[int] = Field(None, ge=1, le=20)
    
    class Config:
        from_attributes = True

class UserMax(UserMaxBase):
    id: int

    class Config:
        from_attributes = True

class ProgressionTemplateBase(BaseModel):
    name: str = Field(..., max_length=255)
    user_max_id: int = Field(...)
    intensity: int = Field(..., ge=1, le=100)
    effort: int = Field(..., ge=1, le=10)
    volume: Optional[int] = Field(None, ge=1)

    @validator('effort')
    def round_effort(cls, v):
        """Round effort to nearest 0.5"""
        return round(v * 2) / 2

class ProgressionTemplateCreate(ProgressionTemplateBase):
    pass

class ProgressionTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    user_max_id: Optional[int] = Field(None)
    intensity: Optional[int] = Field(None, ge=1, le=100)
    effort: Optional[int] = Field(None, ge=1, le=10)
    volume: Optional[int] = Field(None, ge=1)

class ProgressionTemplateResponse(ProgressionTemplateBase):
    id: int
    calculated_weight: Optional[int] = Field(None)
    
    class Config:
        from_attributes = True
