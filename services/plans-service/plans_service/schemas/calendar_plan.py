from pydantic import BaseModel, Field, model_validator, field_validator
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum
from .user_max import UserMaxResponse
from .mesocycle import MesocycleResponse
from .schedule_item import ExerciseScheduleItem, ParamsSets
import json


class CalendarPlanBase(BaseModel):
    """Базовая схема календарного плана"""

    name: str = Field(..., max_length=255)
    schedule: Dict[str, List[ExerciseScheduleItem]]
    duration_weeks: int = Field(..., ge=1)

    class Config:
        from_attributes = True
        json_encoders = {"datetime": lambda v: v.isoformat() if v else None}

    @model_validator(mode="before")
    def _ensure_schedule_dict(cls, values):
        """Гарантируем, что schedule всегда словарь ({}), даже если в БД он NULL.
        Это предотвращает ошибки валидации ответа FastAPI для summary/response моделей.
        """
        # values может быть dict исходных полей ORM-модели
        if isinstance(values, dict):
            sched = values.get("schedule", None)
            if sched is None:
                values["schedule"] = {}
        return values

    @field_validator("schedule", mode="before")
    @classmethod
    def _coerce_schedule_field(cls, v):
        """Дополнительно приводим schedule к dict, если он приходит строкой JSON или None."""
        if v is None:
            return {}
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, dict) else {}
            except Exception:
                return {}
        # если это уже dict — отдаем как есть, дальше провалидируют элементы
        if isinstance(v, dict):
            return v
        return v


class CalendarPlanCreate(BaseModel):
    """Схема для создания плана"""

    name: str = Field(..., max_length=255)
    schedule: Dict[str, List[ExerciseScheduleItem]]
    duration_weeks: int = Field(..., ge=1)


class CalendarPlanUpdate(BaseModel):
    """Схема для частичного обновления плана"""

    name: Optional[str] = None
    schedule: Optional[Dict[str, List[ExerciseScheduleItem]]] = None
    duration_weeks: Optional[int] = Field(default=None, ge=1)


class AppliedCalendarPlanBase(BaseModel):
    """Базовая схема примененного плана"""

    start_date: Optional[datetime] = None
    is_active: bool = True

    class Config:
        from_attributes = True
        json_encoders = {"datetime": lambda v: v.isoformat() if v else None}


class AppliedCalendarPlanCreate(AppliedCalendarPlanBase):
    """Схема для создания примененного плана"""

    calendar_plan_id: int  # ID плана, который применяем
    user_maxes: List[int]  # Список ID user_max для этого плана

    @model_validator(mode="before")
    def validate_start_date(cls, values):
        if "start_date" not in values or values["start_date"] is None:
            values["start_date"] = datetime.utcnow()
        return values


# ===== Apply settings (request) =====
class RoundingMode(str, Enum):
    nearest = "nearest"
    floor = "floor"
    ceil = "ceil"


class ApplyPlanComputeSettings(BaseModel):
    compute_weights: bool = Field(default=True)
    rounding_step: float = Field(default=2.5, gt=0)
    rounding_mode: RoundingMode = Field(default=RoundingMode.nearest)
    generate_workouts: bool = Field(
        default=True,
        description="Generate Workout instances linked to the applied plan",
    )
    start_date: Optional[datetime] = Field(
        default=None, description="Override plan start date"
    )


class ApplyPlanRequest(BaseModel):
    user_max_ids: List[int]
    compute: ApplyPlanComputeSettings = Field(default_factory=ApplyPlanComputeSettings)


class CalendarPlanSummaryResponse(CalendarPlanBase):
    """Облегченная схема ответа для списка планов"""

    id: int
    is_active: bool
    is_favorite: bool = False

    class Config:
        from_attributes = True
        json_encoders = {"datetime": lambda v: v.isoformat() if v else None}


class CalendarPlanNameOnly(BaseModel):
    """Минимальная схема только с идентификатором и названием плана
    Используется внутри AppliedCalendarPlanSummaryResponse для сокращения payload.
    """

    id: int
    name: str

    class Config:
        from_attributes = True


class CalendarPlanResponse(CalendarPlanBase):
    """Схема ответа для плана"""

    id: int
    is_active: bool
    mesocycles: List[MesocycleResponse] = Field(default_factory=list)
    is_favorite: bool = False

    class Config:
        from_attributes = True
        json_encoders = {"datetime": lambda v: v.isoformat() if v else None}


class AppliedCalendarPlanSummaryResponse(AppliedCalendarPlanBase):
    """Облегченная схема ответа для списка примененных планов"""

    id: int
    calendar_plan_id: int
    end_date: datetime
    calendar_plan: CalendarPlanNameOnly  # Минимальная схема плана (id, name)

    class NextWorkoutSummary(BaseModel):
        id: int
        name: str
        scheduled_for: Optional[datetime] = None
        plan_order_index: Optional[int] = None

    next_workout: Optional[NextWorkoutSummary] = Field(default=None)

    class Config:
        from_attributes = True
        json_encoders = {"datetime": lambda v: v.isoformat() if v else None}


class AppliedCalendarPlanResponse(AppliedCalendarPlanBase):
    """Схема ответа для примененного плана"""

    id: int
    calendar_plan_id: int  # ID связанного плана
    end_date: datetime
    calendar_plan: CalendarPlanResponse  # Полный объект плана
    user_maxes: List[UserMaxResponse]  # Полные объекты UserMax
    user_max_ids: List[int] = Field(default_factory=list)
    # Optional: next workout summary for active plans

    class NextWorkoutSummary(BaseModel):
        id: int
        name: str
        scheduled_for: Optional[datetime] = None
        plan_order_index: Optional[int] = None

    next_workout: Optional[NextWorkoutSummary] = Field(default=None)

    class Config:
        from_attributes = True
        json_encoders = {"datetime": lambda v: v.isoformat() if v else None}


# ===== Instances (editable copies) =====
class ParamsSetsInstance(ParamsSets):
    id: int


class ExerciseScheduleItemInstance(BaseModel):
    id: int
    exercise_id: int
    sets: List[ParamsSetsInstance]


class CalendarPlanInstanceBase(BaseModel):
    name: str
    schedule: Dict[str, List[ExerciseScheduleItemInstance]]
    duration_weeks: int = Field(..., ge=1)

    @model_validator(mode="before")
    def _ensure_schedule_dict_instance(cls, values):
        """Для instance также гарантируем пустой словарь по умолчанию вместо NULL."""
        if isinstance(values, dict):
            sched = values.get("schedule", None)
            if sched is None:
                values["schedule"] = {}
        return values

    @field_validator("schedule", mode="before")
    @classmethod
    def _coerce_schedule_field_instance(cls, v):
        """Приводим schedule к dict для instance, если пришла строка JSON или None."""
        if v is None:
            return {}
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, dict) else {}
            except Exception:
                return {}
        if isinstance(v, dict):
            return v
        return v


class CalendarPlanInstanceCreate(BaseModel):
    source_plan_id: Optional[int] = None
    name: str
    schedule: Dict[str, List[ExerciseScheduleItemInstance]]
    duration_weeks: int = Field(..., ge=1)


class CalendarPlanInstanceUpdate(BaseModel):
    name: Optional[str] = None
    schedule: Optional[Dict[str, List[ExerciseScheduleItemInstance]]] = None
    duration_weeks: Optional[int] = Field(default=None, ge=1)


class CalendarPlanInstanceResponse(CalendarPlanInstanceBase):
    id: int
    source_plan_id: Optional[int]

    class Config:
        from_attributes = True
