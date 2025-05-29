from pydantic import BaseModel, Field
from typing import Optional, List, Union, Dict, Any
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
    volume: int
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

class ProgressionsCreate(BaseModel):
    user_max_id: int
    sets: int = Field(ge=1, description="Number of sets (required)")
    intensity: Optional[int] = Field(
        None,
        ge=1,
        le=100,
        description="Intensity as percentage of 1RM (1-100)."
    )
    effort: Optional[float] = Field(
        None,
        ge=1.0,
        le=10.0,
        description="Perceived exertion level (1-10)."
    )
    volume: Optional[int] = Field(
        None,
        ge=1,
        description="Number of repetitions per set."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_max_id": 1,
                "sets": 3,
                "intensity": 75,
                "effort": 8.0,
                "volume": 8
            }
        }
    }

class Progressions(ProgressionsBase):
    id: int
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
        
class LLMProgressionCreate(BaseModel):
    """"""
    user_max_id: int
    user_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for the progression"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "user_max_id": 1,
                "user_data": {}
            }
        }
    }

class LLMProgressionBase(LLMProgressionCreate):
    sets: int = Field(ge=0)
    intensity: int = Field(ge=0, le=100, description="Intensity as a percentage of 1RM (0-100)")
    effort: float = Field(ge=0.0, le=10.0, description="Perceived exertion level (0-10)")
    volume: int = Field(ge=0, description="Number of repetitions per set")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "user_max_id": 1,
                "sets": 3,
                "intensity": 75,
                "effort": 8.0,
                "volume": 8,
                "user_data": {}
            }
        }
    }

class LLMProgressionResponse(LLMProgressionBase):
    id: int
    calculated_weight: float = Field(
        description="Calculated weight based on user's max weight and intensity"
    )
    user_max_display: str = Field(
        description="Display string for the associated user max"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "user_max_id": 1,
                "sets": 3,
                "intensity": 75,
                "effort": 8.0,
                "volume": 8,
                "calculated_weight": 120.0,
                "user_max_display": "Bench Press: 100kg x 5",
                "user_data": {}
            }
        }
    }
    
    @classmethod
    def from_orm(cls, obj):
        data = {
            'id': obj.id,
            'user_max_id': obj.user_max_id,
            'sets': obj.sets if obj.sets is not None else None,
            'intensity': obj.intensity if obj.intensity != 0 else None,
            'effort': float(obj.effort) if obj.effort is not None else None,
            'volume': obj.volume if obj.volume != 0 else None,
            'user_data': obj.user_data or {},
            'calculated_weight': obj.get_calculated_weight(),
            'user_max_display': str(obj.user_max) if hasattr(obj, 'user_max') and obj.user_max else None
        }
        return cls(**data)
    
    model_config = {
        "from_attributes": True,
        "json_encoders": {
            float: lambda v: round(float(v), 2) if v is not None else None
        },
        "json_schema_extra": {
            "example": {
                "id": 1,
                "user_max_id": 1,
                "sets": 3,
                "intensity": 75,
                "effort": 8.0,
                "volume": 8,
                "calculated_weight": 120.0,
                "user_max_display": "Bench Press: 100kg x 5",
                "user_data": {}
            }
        }
    }
