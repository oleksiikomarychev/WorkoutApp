"""Database models for Webhook Dispatcher (read-only)."""

from __future__ import annotations

from datetime import UTC, datetime

from database import Base
from sqlalchemy import Column, DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID


def utc_now() -> datetime:
    """Return current timezone-aware UTC datetime."""
    return datetime.now(UTC)


class WebhookSubscription(Base):
    """Webhook subscription model (read-only for dispatcher)."""

    __tablename__ = "webhook_subscriptions"

    id = Column(PGUUID(as_uuid=True), primary_key=True)
    service = Column(String(50), nullable=False)
    target_url = Column(String(2048), nullable=False)
    secret = Column(String(255), nullable=False)
    events = Column(JSONB, nullable=False)
    filters = Column(JSONB, default=dict, nullable=False)
    active = Column(String(10), nullable=False, default="true")
    lease_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (Index("idx_webhook_subscriptions_active", "active", "service"),)

    def __repr__(self) -> str:
        return f"<WebhookSubscription(id={self.id}, service={self.service}, active={self.active})>"
