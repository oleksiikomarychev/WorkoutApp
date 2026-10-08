"""SQLAlchemy models for Messaging Service."""
from datetime import datetime
from uuid import uuid4

from database import Base
from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship


class Channel(Base):
    """Channel model for messaging channels."""
    
    __tablename__ = "channels"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    type = Column(String(20), nullable=False, index=True)
    name = Column(String(255), nullable=True)  # NULL for direct channels
    app_id = Column(String(50), nullable=True, index=True)
    context_resource = Column(JSONB, nullable=True)
    channel_metadata = Column("metadata", JSONB, default=dict, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    members = relationship("ChannelMember", back_populates="channel", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="channel", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "type IN ('direct', 'group')",
            name="channels_type_check"
        ),
        Index("idx_channels_type", "type"),
    )
    
    def __repr__(self):
        return f"<Channel(id={self.id}, type={self.type}, name={self.name})>"


class ChannelMember(Base):
    """Channel member model for tracking channel membership."""
    
    __tablename__ = "channel_members"
    
    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), primary_key=True)
    joined_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    left_at = Column(DateTime, nullable=True)
    
    # Relationships
    channel = relationship("Channel", back_populates="members")
    
    # Indexes
    __table_args__ = (
        Index("idx_channel_members_user", "user_id", "joined_at", postgresql_where="left_at IS NULL"),
    )
    
    def __repr__(self):
        return f"<ChannelMember(channel_id={self.channel_id}, user_id={self.user_id})>"


class Message(Base):
    """Message model for channel messages."""
    
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    content = Column(Text, nullable=False)
    kind = Column(String(20), nullable=False)
    app_id = Column(String(50), nullable=True, index=True)
    context_resource = Column(JSONB, nullable=True)
    reply_to = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    attachments = Column(JSONB, default=list, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    channel = relationship("Channel", back_populates="messages")
    parent_message = relationship("Message", remote_side=[id], backref="replies")
    acknowledgments = relationship("MessageAcknowledgment", back_populates="message", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "kind IN ('text', 'media', 'system')",
            name="messages_kind_check"
        ),
        Index("idx_messages_channel_created", "channel_id", "created_at", postgresql_where="deleted_at IS NULL"),
    )
    
    def __repr__(self):
        return f"<Message(id={self.id}, channel_id={self.channel_id}, sender_id={self.sender_id}, kind={self.kind})>"


class MessageAcknowledgment(Base):
    """Message acknowledgment model for tracking delivery and read status."""
    
    __tablename__ = "message_acknowledgments"
    
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), primary_key=True)
    status = Column(String(20), primary_key=True)
    acknowledged_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    message = relationship("Message", back_populates="acknowledgments")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('delivered', 'read')",
            name="message_acknowledgments_status_check"
        ),
        Index("idx_acks_message", "message_id", "status"),
    )
    
    def __repr__(self):
        return f"<MessageAcknowledgment(message_id={self.message_id}, user_id={self.user_id}, status={self.status})>"


class IdempotencyKey(Base):
    """Idempotency key model for preventing duplicate operations."""
    
    __tablename__ = "idempotency_keys"
    
    key = Column(String(255), primary_key=True)
    service = Column(String(50), nullable=False)
    endpoint = Column(String(255), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    response_status = Column(Integer, nullable=False)
    response_body = Column(JSONB, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Indexes
    __table_args__ = (
        Index("idx_idempotency_created", "created_at"),
    )
    
    def __repr__(self):
        return f"<IdempotencyKey(key={self.key}, user_id={self.user_id}, endpoint={self.endpoint})>"


class OutboxEvent(Base):
    """Outbox event model for reliable event publishing to Redis Streams."""
    
    __tablename__ = "outbox_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    stream_name = Column(String(255), nullable=False, index=True)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    published_at = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index("idx_outbox_unpublished", "created_at", postgresql_where="published_at IS NULL"),
    )
    
    def __repr__(self):
        status = "published" if self.published_at else "pending"
        return f"<OutboxEvent(id={self.id}, event_type={self.event_type}, status={status})>"


class WebhookSubscription(Base):
    """Webhook subscription model for external integrations."""
    
    __tablename__ = "webhook_subscriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    service = Column(String(50), nullable=False)  # "social" or "messaging"
    target_url = Column(String(2048), nullable=False)
    secret = Column(String(255), nullable=False)  # For HMAC signing
    events = Column(JSONB, nullable=False)  # List of event types to subscribe to
    filters = Column(JSONB, default=dict, nullable=False)  # Additional filters (scope, authors, etc.)
    active = Column(String(10), nullable=False, default="true")  # "true" or "false" as string
    lease_expires_at = Column(DateTime, nullable=True)  # For auto-cleanup
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("idx_webhook_subscriptions_active", "active", "service"),
    )
    
    def __repr__(self):
        return f"<WebhookSubscription(id={self.id}, service={self.service}, target_url={self.target_url}, active={self.active})>"
