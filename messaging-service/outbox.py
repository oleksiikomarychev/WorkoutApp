"""Outbox pattern implementation for reliable event publishing."""
from datetime import datetime
from typing import Any
from uuid import uuid4

from models import OutboxEvent
from sqlalchemy.orm import Session


def create_outbox_event(
    db: Session,
    stream_name: str,
    event_type: str,
    payload: dict[str, Any]
) -> OutboxEvent:
    """Create an outbox event in a database transaction.
    
    This function should be called within the same transaction as the
    business logic to ensure atomicity.
    
    Args:
        db: Database session (should be in an active transaction)
        stream_name: Redis stream name (e.g., "app.messaging.message.created")
        event_type: Event type identifier
        payload: Event payload data
        
    Returns:
        Created OutboxEvent instance
    """
    event = OutboxEvent(
        id=uuid4(),
        stream_name=stream_name,
        event_type=event_type,
        payload=payload,
        created_at=datetime.utcnow(),
        published_at=None,
        retry_count=0
    )
    
    db.add(event)
    # Note: Don't commit here - let the caller commit the transaction
    
    return event


def get_unpublished_events(db: Session, limit: int = 100) -> list[OutboxEvent]:
    """Get unpublished events from the outbox.
    
    Args:
        db: Database session
        limit: Maximum number of events to retrieve
        
    Returns:
        List of unpublished OutboxEvent instances
    """
    return db.query(OutboxEvent).filter(
        OutboxEvent.published_at.is_(None)
    ).order_by(
        OutboxEvent.created_at
    ).limit(limit).all()


def mark_event_published(db: Session, event_id: str) -> bool:
    """Mark an event as published.
    
    Args:
        db: Database session
        event_id: Event UUID
        
    Returns:
        True if event was marked, False if not found
    """
    event = db.query(OutboxEvent).filter(
        OutboxEvent.id == event_id
    ).first()
    
    if not event:
        return False
    
    event.published_at = datetime.utcnow()
    db.commit()
    
    return True


def increment_retry_count(db: Session, event_id: str) -> bool:
    """Increment retry count for an event.
    
    Args:
        db: Database session
        event_id: Event UUID
        
    Returns:
        True if incremented, False if not found
    """
    event = db.query(OutboxEvent).filter(
        OutboxEvent.id == event_id
    ).first()
    
    if not event:
        return False
    
    event.retry_count += 1
    db.commit()
    
    return True


def delete_old_published_events(db: Session, days: int = 7) -> int:
    """Delete published events older than specified days.
    
    Args:
        db: Database session
        days: Number of days to keep published events
        
    Returns:
        Number of deleted events
    """
    from datetime import timedelta
    
    cutoff_time = datetime.utcnow() - timedelta(days=days)
    
    deleted = db.query(OutboxEvent).filter(
        OutboxEvent.published_at.isnot(None),
        OutboxEvent.published_at < cutoff_time
    ).delete()
    
    db.commit()
    
    return deleted
