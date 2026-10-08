"""Database models for Webhook Dispatcher (read-only)."""
from datetime import datetime

from database import Base
from sqlalchemy import Column, DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID


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
    lease_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_webhook_subscriptions_active", "active", "service"),
    )
    
    def __repr__(self):
        return f"<WebhookSubscription(id={self.id}, service={self.service}, active={self.active})>"
