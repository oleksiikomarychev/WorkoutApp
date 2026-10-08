"""SQLAlchemy models for Social Service."""
from datetime import datetime
from uuid import uuid4

from database import Base
from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship


class Post(Base):
    """Post model for social posts."""

    __tablename__ = "posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    author_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    firebase_uid = Column(String(255), nullable=True, index=True)  # Original Firebase UID for author lookup
    content = Column(Text, nullable=False)
    scope = Column(
        String(20),
        nullable=False,
        index=True
    )
    app_id = Column(String(50), nullable=True, index=True)
    context_resource = Column(JSONB, nullable=True)  # {type, id, owner_id}
    attachments = Column(JSONB, default=list, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    reactions = relationship("Reaction", back_populates="post", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "scope IN ('public', 'followers', 'private')",
            name="posts_scope_check"
        ),
        Index("idx_posts_author_created", "author_id", "created_at"),
        Index("idx_posts_scope_created", "scope", "created_at"),
    )
    
    def __repr__(self):
        return f"<Post(id={self.id}, author_id={self.author_id}, scope={self.scope})>"


class Comment(Base):
    """Comment model for post comments."""
    
    __tablename__ = "comments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    content = Column(Text, nullable=False)
    reply_to = Column(UUID(as_uuid=True), ForeignKey("comments.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    post = relationship("Post", back_populates="comments")
    parent_comment = relationship("Comment", remote_side=[id], backref="replies")
    reactions = relationship("Reaction", back_populates="comment", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_comments_post", "post_id", "created_at"),
    )
    
    def __repr__(self):
        return f"<Comment(id={self.id}, post_id={self.post_id}, author_id={self.author_id})>"


class Reaction(Base):
    """Reaction model for posts and comments."""
    
    __tablename__ = "reactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), nullable=True)
    comment_id = Column(UUID(as_uuid=True), ForeignKey("comments.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    type = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    post = relationship("Post", back_populates="reactions")
    comment = relationship("Comment", back_populates="reactions")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "(post_id IS NOT NULL AND comment_id IS NULL) OR (post_id IS NULL AND comment_id IS NOT NULL)",
            name="reactions_target_check"
        ),
        UniqueConstraint("post_id", "user_id", "type", name="uq_reaction_post_user_type"),
        UniqueConstraint("comment_id", "user_id", "type", name="uq_reaction_comment_user_type"),
        Index("idx_reactions_post", "post_id", "type"),
        Index("idx_reactions_comment", "comment_id", "type"),
    )
    
    def __repr__(self):
        target = f"post_id={self.post_id}" if self.post_id else f"comment_id={self.comment_id}"
        return f"<Reaction(id={self.id}, {target}, user_id={self.user_id}, type={self.type})>"


class Follow(Base):
    """Follow model for user subscriptions."""
    
    __tablename__ = "follows"
    
    follower_id = Column(UUID(as_uuid=True), primary_key=True)
    followee_id = Column(UUID(as_uuid=True), primary_key=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "follower_id != followee_id",
            name="follows_no_self_follow_check"
        ),
        Index("idx_follows_followee", "followee_id"),
    )
    
    def __repr__(self):
        return f"<Follow(follower_id={self.follower_id}, followee_id={self.followee_id})>"


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
