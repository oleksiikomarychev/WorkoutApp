"""Unit tests for Redis Streams publisher."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from models import OutboxEvent
from redis_publisher import RedisStreamsPublisher


def test_calculate_retry_delay() -> None:
    pub = RedisStreamsPublisher(redis_url="redis://localhost:6379")
    assert pub.calculate_retry_delay(0) == 60
    assert pub.calculate_retry_delay(1) == 300
    assert pub.calculate_retry_delay(2) == 900
    assert pub.calculate_retry_delay(3) == 3600
    assert pub.calculate_retry_delay(4) == 10800
    # Higher retry counts capped at max delay
    assert pub.calculate_retry_delay(10) == 10800


def test_should_retry_event() -> None:
    pub = RedisStreamsPublisher(redis_url="redis://localhost:6379")

    # Retry count 0 always retries
    event_new = OutboxEvent(id=uuid4(), retry_count=0, created_at=datetime.now(UTC))
    assert pub.should_retry_event(event_new) is True

    # Max retries reached (>=5) never retries
    event_exhausted = OutboxEvent(id=uuid4(), retry_count=5, created_at=datetime.now(UTC))
    assert pub.should_retry_event(event_exhausted) is False

    # Event with retry count 1 created just now (< 60s) should not retry yet
    event_recent = OutboxEvent(id=uuid4(), retry_count=1, created_at=datetime.now(UTC))
    assert pub.should_retry_event(event_recent) is False

    # Event with retry count 1 created 2 minutes ago should retry
    event_ready = OutboxEvent(
        id=uuid4(),
        retry_count=1,
        created_at=datetime.now(UTC) - timedelta(minutes=2),
    )
    assert pub.should_retry_event(event_ready) is True
