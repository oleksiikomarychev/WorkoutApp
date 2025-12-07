from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .calendar import Base


class MesocycleTemplate(Base):
    __tablename__ = "mesocycle_templates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    notes = Column(String(255), nullable=True)

    weeks_count = Column(Integer, nullable=True)
    microcycle_length_days = Column(Integer, nullable=True)
    normalization_value = Column(Integer, nullable=True)
    normalization_unit = Column(String(16), nullable=True)

    is_public = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    microcycles = relationship(
        "MicrocycleTemplate",
        back_populates="mesocycle_template",
        cascade="all, delete-orphan",
        order_by="MicrocycleTemplate.order_index",
    )

    def __repr__(self) -> str:
        return f"<MesocycleTemplate(id={self.id}, name='{self.name}', user_id='{self.user_id}')>"


class MicrocycleTemplate(Base):
    __tablename__ = "microcycle_templates"

    id = Column(Integer, primary_key=True, index=True)
    mesocycle_template_id = Column(
        Integer,
        ForeignKey("mesocycle_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = Column(String(255), nullable=False)
    notes = Column(String(255), nullable=True)
    order_index = Column(Integer, nullable=False, default=0)
    days_count = Column(Integer, nullable=True)

    schedule_json = Column(JSON, nullable=True)

    mesocycle_template = relationship("MesocycleTemplate", back_populates="microcycles")

    def __repr__(self) -> str:
        return (
            "<MicrocycleTemplate("
            f"id={self.id}, meso_tpl_id={self.mesocycle_template_id}, "
            f"name='{self.name}', order={self.order_index})>"
        )
