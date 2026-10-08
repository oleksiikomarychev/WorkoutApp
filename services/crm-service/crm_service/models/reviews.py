from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from ..database import Base


class CoachReview(Base):
    __tablename__ = "coach_reviews"

    id = Column(Integer, primary_key=True, index=True)
    link_id = Column(Integer, ForeignKey("coach_athlete_links.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(String(255), nullable=False, index=True)
    coach_id = Column(String(255), nullable=False, index=True)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("link_id", "reviewer_id", name="uq_link_reviewer"),
        Index("ix_coach_reviews_coach_created", "coach_id", "created_at"),
        Index("ix_coach_reviews_link_reviewer", "link_id", "reviewer_id"),
    )
