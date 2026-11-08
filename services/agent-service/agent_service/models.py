"""SQLAlchemy models for agent-service."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, Integer, LargeBinary, String

from .database import Base


def _utcnow() -> datetime:
    """Return current naive UTC datetime for database column compatibility."""
    return datetime.now(UTC).replace(tzinfo=None)


class GeneratedPlan(Base):
    """Stores full plan generation output associated with a user."""

    __tablename__ = "generated_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    plan_data = Column(JSON, nullable=True)


class Avatar(Base):
    """Stores user avatar images generated or uploaded by users."""

    __tablename__ = "user_avatars"

    user_id = Column(String(255), primary_key=True, index=True)
    content_type = Column(String(64), default="image/png", nullable=False)
    image = Column(LargeBinary, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)
