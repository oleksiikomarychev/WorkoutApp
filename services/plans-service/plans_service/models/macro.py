from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .calendar import Base, _utc_now


class PlanMacro(Base):
    __tablename__ = "plan_macros"

    id = Column(Integer, primary_key=True, index=True)
    calendar_plan_id = Column(Integer, ForeignKey("calendar_plans.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    priority = Column(Integer, nullable=False, default=100)

    rule_json = Column(Text, nullable=False)

    created_at = Column(DateTime, default=_utc_now, nullable=False)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now, nullable=False)

    calendar_plan = relationship("CalendarPlan", back_populates="macros", passive_deletes=True)
