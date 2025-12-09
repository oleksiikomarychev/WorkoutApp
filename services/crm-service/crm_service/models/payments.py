from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from ..database import Base


class CoachAthletePayment(Base):
    __tablename__ = "coach_athlete_payments"

    id = Column(Integer, primary_key=True, index=True)
    stripe_checkout_session_id = Column(String(255), nullable=False, unique=True, index=True)
    stripe_payment_intent_id = Column(String(255), nullable=True, unique=True, index=True)

    coach_id = Column(String(255), nullable=False, index=True)
    athlete_id = Column(String(255), nullable=False, index=True)
    link_id = Column(Integer, ForeignKey("coach_athlete_links.id", ondelete="SET NULL"), nullable=True, index=True)

    currency = Column(String(3), nullable=False)
    amount_minor = Column(Integer, nullable=False)

    status = Column(String(32), nullable=False, index=True, default="pending")
    valid_until = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
