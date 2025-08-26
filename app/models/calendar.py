from sqlalchemy import Column, Integer, String, ForeignKey, JSON, DateTime, Boolean, text, Float
from sqlalchemy.orm import relationship
from app.database import Base
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

# Association table for many-to-many relationship between AppliedCalendarPlan and UserMax
class AppliedCalendarPlanUserMax(Base):
    __tablename__ = "applied_calendar_plan_user_maxes"

    applied_calendar_plan_id = Column(Integer, ForeignKey("applied_calendar_plans.id", ondelete="CASCADE"), primary_key=True)
    user_max_id = Column(Integer, ForeignKey("user_maxes.id", ondelete="CASCADE"), primary_key=True)

class CalendarPlan(Base):
    __tablename__ = "calendar_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    schedule: Dict[str, List[Dict[str, Any]]] = Column(JSON, nullable=False)
    duration_weeks = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    
    applied_plans = relationship("AppliedCalendarPlan", back_populates="calendar_plan", cascade="all, delete-orphan")
    # New: hierarchical structure support
    mesocycles = relationship(
        "Mesocycle",
        back_populates="calendar_plan",
        cascade="all, delete-orphan",
        order_by="Mesocycle.order_index",
    )

    def __repr__(self):
        return f"<CalendarPlan(id={self.id}, name='{self.name}')>"

    class Config:
        from_attributes = True

class AppliedCalendarPlan(Base):
    __tablename__ = "applied_calendar_plans"

    id = Column(Integer, primary_key=True, index=True)

    class Config:
        from_attributes = True
    calendar_plan_id = Column(Integer, ForeignKey("calendar_plans.id", ondelete="CASCADE"), nullable=False)
    start_date = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)

    calendar_plan = relationship("CalendarPlan", back_populates="applied_plans")
    user_maxes = relationship("UserMax", back_populates="applied_plans", secondary="applied_calendar_plan_user_maxes")
    # Link generated workouts
    workouts = relationship("Workout", back_populates="applied_plan", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AppliedCalendarPlan(id={self.id}, calendar_plan_id={self.calendar_plan_id}, start_date={self.start_date}, end_date={self.end_date})>"

    def calculate_end_date(self, duration_weeks: int):
        """Вычисляет дату окончания плана на основе продолжительности"""
        self.end_date = self.start_date + timedelta(weeks=duration_weeks)
        return self.end_date

# ===== New hierarchical plan models =====

class Mesocycle(Base):
    __tablename__ = "mesocycles"

    id = Column(Integer, primary_key=True, index=True)
    calendar_plan_id = Column(Integer, ForeignKey("calendar_plans.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    notes = Column(String(100), nullable=True)
    order_index = Column(Integer, nullable=False, default=0)
    normalization_value = Column(Float, nullable=True)
    normalization_unit = Column(String(16), nullable=True)
    # Normalization fields for plan structure
    weeks_count = Column(Integer, nullable=True)
    microcycle_length_days = Column(Integer, nullable=True)

    calendar_plan = relationship("CalendarPlan", back_populates="mesocycles")
    microcycles = relationship(
        "Microcycle",
        back_populates="mesocycle",
        cascade="all, delete-orphan",
        order_by="Microcycle.order_index",
    )

    def __repr__(self):
        return f"<Mesocycle(id={self.id}, plan_id={self.calendar_plan_id}, name='{self.name}', order={self.order_index})>"


class Microcycle(Base):
    __tablename__ = "microcycles"

    id = Column(Integer, primary_key=True, index=True)
    mesocycle_id = Column(Integer, ForeignKey("mesocycles.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    notes = Column(String(100), nullable=True)
    order_index = Column(Integer, nullable=False, default=0)
    # Schedule for a single microcycle (week) — days -> exercises
    schedule: Dict[str, List[Dict[str, Any]]] = Column(JSON, nullable=False)
    normalization_value = Column(Float, nullable=True)
    normalization_unit = Column(String(16), nullable=True)
    # Length of this microcycle (days)
    days_count = Column(Integer, nullable=True)

    mesocycle = relationship("Mesocycle", back_populates="microcycles")

    def __repr__(self):
        return f"<Microcycle(id={self.id}, mesocycle_id={self.mesocycle_id}, name='{self.name}', order={self.order_index})>"

# Favorite calendar plans (saved by user). Note: user context not implemented yet
class FavoriteCalendarPlan(Base):
    __tablename__ = "favorite_calendar_plans"

    id = Column(Integer, primary_key=True, index=True)
    calendar_plan_id = Column(Integer, ForeignKey("calendar_plans.id", ondelete="CASCADE"), unique=True, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    calendar_plan = relationship("CalendarPlan")

    def __repr__(self):
        return f"<FavoriteCalendarPlan(id={self.id}, calendar_plan_id={self.calendar_plan_id})>"

# Editable copy of a calendar plan (instance). Global scope (no user yet)
class CalendarPlanInstance(Base):
    __tablename__ = "calendar_plan_instances"

    id = Column(Integer, primary_key=True, index=True)
    source_plan_id = Column(Integer, ForeignKey("calendar_plans.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=False)
    schedule: Dict[str, List[Dict[str, Any]]] = Column(JSON, nullable=False)
    duration_weeks = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))

    source_plan = relationship("CalendarPlan")

    def __repr__(self):
        return f"<CalendarPlanInstance(id={self.id}, source_plan_id={self.source_plan_id}, name='{self.name}')>"
