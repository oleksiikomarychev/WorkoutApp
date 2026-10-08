from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class UnitType(str, Enum):
    GRAM = "g"
    MILLIGRAM = "mg"
    MICROGRAM = "mcg"
    KCAL = "kcal"
    MILLILITER = "ml"
    IU = "IU"
    UNIT = "U"

class BaseEntry(BaseModel):
    name: str
    unit: UnitType
    dosage: float = Field(..., gt=0)

class Food(BaseEntry):
    calories: float = 0
    proteins: float = 0
    fats: float = 0
    carbs: float = 0
    weight_g: float = Field(..., gt=0)

class Supplement(BaseEntry):
    pass

class Medication(BaseEntry):
    half_life_hours: float | None = None
    
    concentration: float | None = Field(None, description="Количество вещества на 1 мл или 1 единицу")

    @property
    def total_active_substance(self) -> float:
        if self.concentration:
            return self.dosage * self.concentration
        return self.dosage


class SessionData(BaseModel):
    id: int | None = None
    user_id: int
    session_id: str
    entries: list[BaseEntry]
    workout_id: int | None = None
    applied_plan_workout_id: int | None = None
    date: datetime

class FoodResponse(BaseModel):
    id: int
    name: str
    unit: UnitType
    dosage: float
    calories: float
    proteins: float
    fats: float
    carbs: float
    weight_g: float
    created_at: str

class SupplementResponse(BaseModel):
    id: int
    name: str
    unit: UnitType
    dosage: float
    created_at: str

class MedicationResponse(BaseModel):
    id: int
    name: str
    unit: UnitType
    dosage: float
    half_life_hours: float | None
    concentration: float | None
    created_at: str

class SessionDataResponse(BaseModel):
    id: int
    user_id: int
    session_id: str
    entries: list[BaseEntry]
    workout_id: int | None
    applied_plan_workout_id: int | None
    date: str