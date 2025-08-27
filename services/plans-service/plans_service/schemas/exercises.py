from pydantic import BaseModel, Field, computed_field, validator, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from typing import Generic, TypeVar, Annotated

class EffortType(str, Enum):
    RPE = "RPE"
    RIR = "RIR"

class MovementType(str, Enum):
    compound = "compound"
    isolation = "isolation"

class Region(str, Enum):
    upper = "upper"
    lower = "lower"

class ExerciseListBase(BaseModel):
    name: str = Field(..., max_length=255)
    muscle_group: Optional[str] = Field(None)
    equipment: Optional[str] = Field(None)
    # New optional detailed muscle fields
    target_muscles: Optional[List[str]] = Field(None, description="Primary target muscles")
    synergist_muscles: Optional[List[str]] = Field(None, description="Synergist muscles involved")
    # New optional classification fields
    movement_type: Optional[MovementType] = Field(None, description="compound or isolation")
    region: Optional[Region] = Field(None, description="upper or lower")

class ExerciseListCreate(ExerciseListBase):
    pass

class ExerciseList(ExerciseListBase):
    id: int

    class Config:
        from_attributes = True

class SetBase(BaseModel):
    """Базовая схема сета"""
    pass

class ExerciseSet(SetBase):
    """Схема выполненного сета"""
    id: Optional[int] = Field(None, description="ID сета в рамках инстанса")
    weight: Optional[float] = Field(None, ge=0, description="Вес в кг (может быть дробным)")
    volume: Optional[int] = Field(None, ge=1, description="Объем")
    # Новые опциональные поля для RPE-параметров (валидацию переносим на уровень бизнес-логики)
    intensity: Optional[int] = Field(None, description="Интенсивность, % от 1ПМ")
    effort: Optional[int] = Field(None, description="Усилие RPE/RIR")

    class Config:
        # Важно: сохранять дополнительные поля (reps, rpe, order, и т.п.)
        extra = 'allow'

class ExerciseSetUpdate(BaseModel):
    """Схема обновления сета (частичное обновление)."""
    weight: Optional[float] = Field(None, ge=0)
    volume: Optional[int] = Field(None, ge=1)
    reps: Optional[int] = Field(None, ge=0)
    rpe: Optional[float] = Field(None, ge=0)
    order: Optional[int] = Field(None, ge=0)
    # Те же поля и ограничения для частичного обновления
    intensity: Optional[int] = Field(None, ge=40, le=100)
    effort: Optional[int] = Field(None, ge=4, le=10)

    class Config:
        # Разрешаем дополнительные произвольные поля, чтобы не ограничивать формат сетов
        extra = 'allow'

class ExerciseInstanceBase(BaseModel):
    exercise_list_id: int = Field(...)
    sets: List[ExerciseSet] = Field(...)
    # Optional metadata fields
    notes: Optional[str] = Field(None, description="Free-form notes for the exercise instance")
    order: Optional[int] = Field(None, ge=0, description="Position/order of the exercise in the workout")

    class Config:
        from_attributes = True
        json_encoders = {
            'datetime': lambda v: v.isoformat() if v else None
        }

class ExerciseInstanceCreate(ExerciseInstanceBase):
    user_max_id: Optional[int] = Field(None, description="ID of the user's maximum for this exercise")

class ExerciseInstance(ExerciseInstanceBase):
    id: int
    # Expose linkage fields for responses
    workout_id: Optional[int] = None
    user_max_id: Optional[int] = None
    # Optional metadata
    notes: Optional[str] = None
    order: Optional[int] = None
    # Lightweight embedded definition
    exercise_definition: Optional[ExerciseList] = None

    class Config:
        from_attributes = True
        json_encoders = {
            'datetime': lambda v: v.isoformat() if v else None
        }

class ExerciseInstanceResponse(ExerciseInstanceBase):
    id: int
    # Expose linkage fields for responses
    workout_id: Optional[int] = None
    user_max_id: Optional[int] = None
    # Optional metadata
    notes: Optional[str] = None
    order: Optional[int] = None
    # Lightweight embedded definition
    exercise_definition: Optional[ExerciseList] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            'datetime': lambda v: v.isoformat() if v else None
        }

class ExerciseListResponse(ExerciseListBase):
    id: int

    class Config:
        from_attributes = True
        json_encoders = {
            'datetime': lambda v: v.isoformat() if v else None
        }
