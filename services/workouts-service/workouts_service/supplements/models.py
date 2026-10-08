import os
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String, create_engine, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .schemas import UnitType


class SupplementsBase(DeclarativeBase):
    pass

class TimestampMixin:
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    name: Mapped[str] = mapped_column(String(100))

class FoodModel(TimestampMixin, SupplementsBase):
    __tablename__ = "food"
    
    dosage: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(SQLEnum(UnitType))
    calories: Mapped[float] = mapped_column(Float, default=0)
    proteins: Mapped[float] = mapped_column(Float, default=0)
    fats: Mapped[float] = mapped_column(Float, default=0)
    carbs: Mapped[float] = mapped_column(Float, default=0)
    weight_g: Mapped[float] = mapped_column(Float)

class SupplementModel(TimestampMixin, SupplementsBase):
    __tablename__ = "supplements"
    
    dosage: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(SQLEnum(UnitType))

class MedicationModel(TimestampMixin, SupplementsBase):
    __tablename__ = "medications"
    
    dosage: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(SQLEnum(UnitType))
    half_life_hours: Mapped[float | None] = mapped_column(Float)
    concentration: Mapped[float | None] = mapped_column(Float)

    def __repr__(self) -> str:
        return f"<Medication(name={self.name!r}, dosage={self.dosage}{self.unit.value})>"

class SessionDataModel(SupplementsBase):
    __tablename__ = "session_data"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer)
    session_id: Mapped[str] = mapped_column(String(100))
    entries: Mapped[list[dict]] = mapped_column(JSON)
    workout_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    applied_plan_workout_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    date: Mapped[datetime] = mapped_column(DateTime)

DATABASE_URL = os.getenv("SUPPLEMENTS_DATABASE_URL")
engine = create_engine(DATABASE_URL, echo=True)

SupplementsBase.metadata.create_all(engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
