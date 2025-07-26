from pydantic import BaseModel, Field, computed_field, validator
from typing import Optional, List, Dict, Any
from enum import Enum

class EffortType(str, Enum):
    RPE = "RPE"
    RIR = "RIR"

class WorkoutSetsAndReps(BaseModel):
    sets: int = Field(..., ge=1)
    reps: int = Field(..., ge=1)

class WorkoutSetsAndRepsUpdate(BaseModel):
    sets: Optional[int] = Field(None, ge=1)
    reps: Optional[int] = Field(None, ge=1)


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

class WorkoutWithCalculatedWeight(WorkoutResponse):
    calculated_weight: Optional[float] = Field(None)

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
    weight: Optional[int] = Field(None, ge=0)
    sets_and_reps: List[WorkoutSetsAndReps] = Field(..., description="Sets and reps for the exercise")
    
    class Config:
        from_attributes = True
        json_encoders = {
            'datetime': lambda v: v.isoformat() if v else None
        }

class ExerciseInstanceCreate(ExerciseInstanceBase):
    user_max_id: Optional[int] = Field(None, description="ID of the user's maximum for this exercise")

class ExerciseInstanceCreateWithWorkout(BaseModel):
    exercise_list_id: int = Field(...)
    user_max_id: Optional[int] = Field(None, description="ID of the user's maximum for this exercise")
    weight: Optional[int] = Field(None, ge=0)
    
    class Config:
        json_encoders = {
            'datetime': lambda v: v.isoformat() if v else None
        }

class ExerciseInstance(ExerciseInstanceBase):
    id: int

    class Config:
        from_attributes = True
        json_encoders = {
            'datetime': lambda v: v.isoformat() if v else None
        } 

class ExerciseInstanceResponse(ExerciseInstanceBase):
    id: int
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
            'weight': obj.weight,
            'sets_and_reps': getattr(obj, 'sets_and_reps', []),
        }
        
        if hasattr(obj, 'progression_template') and obj.progression_template:
            data['progression_template'] = ProgressionTemplateResponse(
                id=obj.progression_template.id,
                name=obj.progression_template.name,
                calculated_weight=getattr(obj.progression_template, 'calculated_weight', None)
            )
            
            # Add progression parameters from the linking table
            data['volume'] = obj.progression_template.volume
            data['intensity'] = obj.progression_template.intensity
            data['effort'] = obj.progression_template.effort
            
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

class ProgressionTemplateCreate(ProgressionTemplateBase):
    pass

class ProgressionTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)

class ProgressionTemplateResponse(ProgressionTemplateBase):
    id: int
    name: str
    
    class Config:
        from_attributes = True
        json_encoders = {
            'datetime': lambda v: v.isoformat() if v else None
        }


class ProgressionSet(BaseModel):
    """Schema for a single set in a progression instance"""
    intensity: Optional[int] = Field(None, ge=1, le=100, description="Intensity as a percentage of 1RM")
    volume: Optional[int] = Field(None, ge=1, description="Number of reps for this set")
    effort: Optional[int] = Field(None, ge=1, le=10, description="RPE/RIR value for this set")

class ExerciseInstanceWithProgressionTemplateBase(BaseModel):
    """Base schema for progression instances with the new format"""
    sets: List[ProgressionSet] = Field(..., description="List of sets with their parameters")

class ExerciseInstanceWithProgressionTemplate(ExerciseInstanceWithProgressionTemplateBase):
    """Schema for creating a new progression instance"""
    pass

class ExerciseInstanceWithProgressionTemplateUpdate(BaseModel):
    """Schema for updating an existing progression instance"""
    sets: Optional[List[ProgressionSet]] = Field(None, description="List of sets with their parameters")