from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class EffortType(str, Enum):
    RPE = "RPE"
    RIR = "RIR"


class MovementType(str, Enum):
    compound = "compound"
    isolation = "isolation"


class Region(str, Enum):
    upper = "upper"
    lower = "lower"



class MuscleInfo(BaseModel):
    key: str
    label: str
    group: str


class ExerciseListBase(BaseModel):
    name: str = Field(..., max_length=255)
    muscle_group: Optional[str] = None
    equipment: Optional[str] = None
    target_muscles: Optional[List[str]] = Field(
        None, description="Primary target muscles"
    )
    synergist_muscles: Optional[List[str]] = Field(
        None, description="Synergist muscles involved"
    )
    movement_type: Optional[MovementType] = Field(
        None, description="compound or isolation"
    )
    region: Optional[Region] = Field(None, description="upper or lower")
    category: Optional[str] = Field(
        None, description="Logical category, e.g. main_lift/accessory/isolation/conditioning"
    )
    movement_pattern: Optional[str] = Field(
        None, description="Movement pattern, e.g. horizontal_press/hinge/squat/row"
    )
    is_competition_lift: Optional[bool] = Field(
        None, description="Whether this exercise is a competition lift variant"
    )


class ExerciseListCreate(ExerciseListBase):
    pass


class ExerciseListResponse(ExerciseListBase):
    id: int

    class Config:
        from_attributes = True


class ExerciseSet(BaseModel):
    id: Optional[int] = Field(None, description="ID of the set within the instance")
    weight: Optional[float] = Field(None, ge=0, description="Weight in kg")
    volume: Optional[int] = Field(None, ge=1, description="Volume")
    intensity: Optional[int] = Field(None, description="Intensity, % of 1RM")
    effort_type: Optional[EffortType] = Field(None, description="Type of effort")
    effort: Optional[int] = Field(None, description="Effort value")

    class Config:
        extra = "allow"  # keep extra fields like reps/rpe/order etc.


class ExerciseSetUpdate(BaseModel):
    weight: Optional[float] = Field(None, ge=0)
    volume: Optional[int] = Field(None, ge=1)
    reps: Optional[int] = Field(None, ge=0)
    effort: Optional[int] = Field(None, ge=4, le=10)

    class Config:
        extra = "allow"


class ExerciseInstanceBase(BaseModel):
    exercise_list_id: int
    sets: List[ExerciseSet]
    notes: Optional[str] = None
    order: Optional[int] = None

    class Config:
        from_attributes = True


class ExerciseInstanceCreate(ExerciseInstanceBase):
    user_max_id: Optional[int] = None


class ExerciseInstanceResponse(ExerciseInstanceBase):
    id: int
    workout_id: Optional[int] = None
    user_max_id: Optional[int] = None
    # exercise_definition: Optional[ExerciseListResponse] = None

    class Config:
        from_attributes = True
