from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from .database import Base


class CalendarPlan(Base):
    __tablename__ = "calendar_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    schedule = Column(Text, nullable=False)  # JSON string
    duration_weeks = Column(Integer, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    is_favorite = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class AppliedCalendarPlan(Base):
    """Applied plan meta (Phase 3 scaffolding)."""
    __tablename__ = "applied_calendar_plans"

    id = Column(Integer, primary_key=True, index=True)
    calendar_plan_id = Column(Integer, ForeignKey("calendar_plans.id", ondelete="CASCADE"), nullable=False)
    start_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    is_active = Column(Boolean, nullable=False, default=True)


class AppliedCalendarPlanUserMax(Base):
    """Link table: applied plan -> user max ids (no external FK)."""
    __tablename__ = "applied_calendar_plan_user_maxes"

    applied_calendar_plan_id = Column(Integer, ForeignKey("applied_calendar_plans.id", ondelete="CASCADE"), primary_key=True)
    user_max_id = Column(Integer, primary_key=True)


class CalendarPlanInstance(Base):
    """Editable copy of a calendar plan (Phase 2)."""
    __tablename__ = "calendar_plan_instances"

    id = Column(Integer, primary_key=True, index=True)
    source_plan_id = Column(Integer, ForeignKey("calendar_plans.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=False)
    schedule = Column(Text, nullable=False)  # JSON string
    duration_weeks = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
