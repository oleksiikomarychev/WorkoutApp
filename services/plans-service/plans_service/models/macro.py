from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

# IMPORTANT: reuse the same Base as other plan models
from .calendar import Base


class PlanMacro(Base):
    __tablename__ = "plan_macros"

    id = Column(Integer, primary_key=True, index=True)
    calendar_plan_id = Column(Integer, ForeignKey("calendar_plans.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    priority = Column(Integer, nullable=False, default=100)

    # JSON stored as text (let alembic/migration promote to JSON if needed later)
    rule_json = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # relationships
    calendar_plan = relationship("CalendarPlan", back_populates="macros", passive_deletes=True)
