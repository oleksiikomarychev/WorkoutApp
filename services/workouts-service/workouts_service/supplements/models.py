from __future__ import annotations

import os
from datetime import datetime

import structlog
from sqlalchemy import JSON, DateTime, Float, Integer, String, create_engine, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from ..config import settings
from .schemas import UnitType

logger = structlog.get_logger(__name__)


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


raw_supp_url = settings.SUPPLEMENTS_DATABASE_URL or os.getenv("SUPPLEMENTS_DATABASE_URL")
if not raw_supp_url:
    raw_supp_url = "sqlite:///:memory:"
elif "host.docker.internal" in raw_supp_url and not (
    os.getenv("DOCKER_CONTAINER") or os.path.exists("/.dockerenv")
):
    raw_supp_url = raw_supp_url.replace("host.docker.internal", "localhost")

try:
    engine = create_engine(raw_supp_url, echo=False)
    SupplementsBase.metadata.create_all(engine)
except Exception:
    logger.warning("Supplements DB connection failed; falling back to in-memory sqlite")
    engine = create_engine("sqlite:///:memory:", echo=False)
    SupplementsBase.metadata.create_all(engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
