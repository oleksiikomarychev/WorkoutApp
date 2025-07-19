from pydantic import BaseModel, Field, computed_field, validator
from typing import Optional, List
from enum import Enum

class EffortType(str, Enum):
    RPE = "RPE"
    RIR = "RIR"


class WorkoutBase(BaseModel):
    name: str = Field(..., max_length=255)

class WorkoutCreate(WorkoutBase):
    pass

class Workout(WorkoutBase):
    id: int
    exercise_instances: List['ExerciseInstance'] = []

    class Config:
        from_attributes = True
        json_encoders = {
            'datetime': lambda v: v.isoformat() if v else None
        }

class WorkoutResponse(WorkoutBase):
    id: int
    exercise_instances: List['ExerciseInstance'] = []
    
    class Config:
        from_attributes = True
        json_encoders = {
            'datetime': lambda v: v.isoformat() if v else None
        }

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

class ExerciseInstanceBase(BaseModel):
    workout_id: int = Field(...)
    exercise_list_id: int = Field(...)
    progression_template_id: Optional[int] = Field(None)
    volume: Optional[int] = Field(None, ge=0)
    intensity: Optional[int] = Field(None, ge=0, le=100)
    effort: Optional[int] = Field(None, ge=0, le=10)
    weight: Optional[int] = Field(None, ge=0)
    
    class Config:
        from_attributes = True
        json_encoders = {
            'datetime': lambda v: v.isoformat() if v else None
        }

class ExerciseInstanceCreate(ExerciseInstanceBase):
    pass

class ExerciseInstanceCreateWithWorkout(BaseModel):
    exercise_list_id: int = Field(...)
    progression_template_id: Optional[int] = Field(None)
    volume: Optional[int] = Field(None, ge=0)
    weight: Optional[int] = Field(None, ge=0)
    intensity: Optional[int] = Field(None, ge=0, le=100)
    effort: Optional[int] = Field(None, ge=0, le=10)
    
    class Config:
        json_encoders = {
            'datetime': lambda v: v.isoformat() if v else None
        }

class ExerciseInstance(ExerciseInstanceBase):
    id: int

    @computed_field
    @property
    def exercise_id(self) -> int:
        return self.exercise_list_id

    exercise_definition: Optional[ExerciseList] = Field(None)
    progression_template: Optional['ProgressionTemplateResponse'] = Field(None)

    class Config:
        from_attributes = True
        json_encoders = {
            'datetime': lambda v: v.isoformat() if v else None
        }

class ExerciseInstanceResponse(ExerciseInstanceBase):
    id: int
    exercise_definition: Optional[ExerciseList] = Field(None)
    progression_template: Optional['ProgressionTemplateResponse'] = Field(None)
    
    class Config:
        from_attributes = True
        
    @classmethod
    def from_orm(cls, obj):
        if obj is None:
            return None
            
        data = {
            'id': obj.id,
            'workout_id': obj.workout_id,
            'exercise_list_id': obj.exercise_list_id,
            'progression_template_id': obj.progression_template_id,
            'volume': obj.volume,
            'intensity': obj.intensity,
            'effort': obj.effort,
            'weight': obj.weight,
            'exercise_definition': ExerciseList.from_orm(obj.exercise_definition) if obj.exercise_definition else None,
        }
        
        if hasattr(obj, 'progression_template') and obj.progression_template:
            data['progression_template'] = ProgressionTemplateResponse(
                id=obj.progression_template.id,
                name=obj.progression_template.name,
                calculated_weight=getattr(obj.progression_template, 'calculated_weight', None)
            )
            
        return cls(**data)

class UserMaxBase(BaseModel):
    exercise_id: int
    max_weight: int
    rep_max: int

class UserMaxCreate(UserMaxBase):
    pass

class UserMax(UserMaxBase):
    id: int

    class Config:
        orm_mode = True

class ProgressionTemplateBase(BaseModel):
    name: str = Field(..., max_length=255)
    user_max_id: int = Field(...)
    intensity: int = Field(..., ge=1, le=100)
    effort: int = Field(..., ge=1, le=10)
    volume: Optional[int] = Field(None, ge=1)

    @validator('effort')
    def round_effort(cls, v):
        # Round to nearest 0.5 and convert to int
        return int(round(v * 2) / 2)

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
    name: str
    calculated_weight: Optional[float] = Field(None)
    volume: Optional[int] = Field(None)
    
    class Config:
        from_attributes = True
        json_encoders = {
            'datetime': lambda v: v.isoformat() if v else None
        }
