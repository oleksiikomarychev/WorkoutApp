"""Unit tests for Webhook Dispatcher service."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest
from config import Settings
from database import normalize_sync_database_url
from delivery import DeliveryResult, WebhookDelivery
from event_processor import EventProcessor
from models import WebhookSubscription
from redis_client import RedisStreamClient
from stream_consumer import StreamConsumer
from webhook_manager import WebhookManager


def test_config_settings_defaults_and_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that Settings respects aliases and ignores extra environment variables."""
    monkeypatch.setenv("REDIS_URL", "redis://redis-test:6379")
    monkeypatch.setenv("WEBHOOK_TIMEOUT", "15")
    monkeypatch.setenv("WEBHOOK_MAX_RETRIES", "7")
    monkeypatch.setenv("SOME_UNKNOWN_VAR", "ignored_value")

    s = Settings()
    assert s.redis_url == "redis://redis-test:6379"
    assert s.delivery_timeout == 15
    assert s.max_retries == 7


def test_database_url_normalization() -> None:
    """Test sync PostgreSQL URL normalization."""
    assert (
        normalize_sync_database_url("postgresql://user:pass@host:5432/db")
        == "postgresql+psycopg2://user:pass@host:5432/db"
    )
    assert (
        normalize_sync_database_url("postgresql+asyncpg://user:pass@host:5432/db")
        == "postgresql+psycopg2://user:pass@host:5432/db"
    )
    assert (
        normalize_sync_database_url("postgresql+psycopg2://user:pass@host:5432/db")
        == "postgresql+psycopg2://user:pass@host:5432/db"
    )
    assert normalize_sync_database_url("sqlite:///./test.db") == "sqlite:///./test.db"


def test_hmac_signature_generation() -> None:
    """Test HMAC SHA256 signature calculation matches standard specification."""
    delivery = WebhookDelivery()
    payload = b'{"hello": "world"}'
    secret = "secret-key-123"

    expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    assert delivery.generate_signature(payload, secret) == expected


def test_retry_delay_calculation() -> None:
    """Test exponential backoff delays and bounds."""
    delivery = WebhookDelivery()
    assert delivery.get_retry_delay(0) == 60
    assert delivery.get_retry_delay(1) == 300
    assert delivery.get_retry_delay(2) == 900
    assert delivery.get_retry_delay(3) == 3600
    assert delivery.get_retry_delay(4) == 10800
    # Greater than max index uses last delay
    assert delivery.get_retry_delay(10) == 10800
    # Negative index handled gracefully
    assert delivery.get_retry_delay(-1) == 60


def test_should_retry_rules() -> None:
    """Test HTTP status code and network error retry classification."""
    delivery = WebhookDelivery()
    # Network / timeout errors
    assert delivery.should_retry(None, "Timeout") is True
    # Server errors (5xx)
    assert delivery.should_retry(500, "Internal Server Error") is True
    assert delivery.should_retry(502, "Bad Gateway") is True
    assert delivery.should_retry(503, "Service Unavailable") is True
    # Rate limiting (429)
    assert delivery.should_retry(429, "Too Many Requests") is True
    # Client errors (4xx except 429) should NOT retry
    assert delivery.should_retry(400, "Bad Request") is False
    assert delivery.should_retry(401, "Unauthorized") is False
    assert delivery.should_retry(404, "Not Found") is False
    assert delivery.should_retry(422, "Unprocessable Entity") is False


@pytest.mark.asyncio
async def test_webhook_delivery_success() -> None:
    """Test successful webhook delivery returns tuple-compatible DeliveryResult."""
    delivery = WebhookDelivery()
    sub = WebhookSubscription(
        id=uuid4(),
        service="social",
        target_url="https://example.com/webhook",
        secret="test-secret",
        events=["post.created"],
    )

    mock_response = MagicMock(status_code=200)
    with patch.object(delivery.http_client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await delivery.deliver(sub, {"event_type": "post.created", "post_id": "123"})

        assert result.success is True
        assert result.status_code == 200
        assert result.error_message is None
        # Verify tuple unpacking compatibility
        success, code, err, del_id = result
        assert success is True
        assert code == 200
        assert err is None
        assert del_id == result.delivery_id


@pytest.mark.asyncio
async def test_webhook_delivery_timeout() -> None:
    """Test webhook delivery timeout handling."""
    delivery = WebhookDelivery()
    sub = WebhookSubscription(
        id=uuid4(),
        service="social",
        target_url="https://example.com/webhook",
        secret="test-secret",
        events=["post.created"],
    )

    with patch.object(delivery.http_client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Read timeout")
        result = await delivery.deliver(sub, {"event_type": "post.created"})

        assert result.success is False
        assert result.status_code is None
        assert result.error_message == "Timeout"


def test_redis_client_unconnected_guard() -> None:
    """Test that RedisStreamClient raises RuntimeError when methods are called before connect()."""
    client = RedisStreamClient()
    with pytest.raises(RuntimeError, match="Redis client is not connected"):
        client.create_consumer_group("stream", "group")

    with pytest.raises(RuntimeError, match="Redis client is not connected"):
        client.read_events({"s": ">"}, "group", "c1")


def test_stream_consumer_parses_unpacked_event_payload() -> None:
    """Test that stream consumer correctly reconstructs payload unpacked by redis_publisher."""
    consumer = StreamConsumer()
    # Format produced by social-service and messaging-service redis_publisher
    raw_message = {
        "event_id": str(uuid4()),
        "event_type": "post.created",
        "timestamp": datetime.now(UTC).isoformat(),
        "post_id": "p-100",
        "author_id": "a-200",
        "scope": "public",
        "extra_dict": json.dumps({"tags": ["workout", "fitness"]}),
    }

    event = consumer._parse_event("app.social.post.created", "1700000000-0", raw_message)
    assert event is not None
    assert event["service"] == "social"
    assert event["event_type"] == "post.created"
    assert event["payload"]["post_id"] == "p-100"
    assert event["payload"]["author_id"] == "a-200"
    assert event["payload"]["scope"] == "public"
    assert event["payload"]["extra_dict"] == {"tags": ["workout", "fitness"]}


def test_stream_consumer_parses_explicit_nested_payload() -> None:
    """Test that stream consumer supports explicit nested payload string or dict."""
    consumer = StreamConsumer()
    raw_message = {
        "payload": json.dumps({"channel_id": "ch-1", "message_id": "msg-99"}),
    }

    event = consumer._parse_event("app.messaging.message.created", "1700000001-0", raw_message)
    assert event is not None
    assert event["service"] == "messaging"
    assert event["event_type"] == "message.created"
    assert event["payload"]["channel_id"] == "ch-1"
    assert event["payload"]["message_id"] == "msg-99"


def test_stream_consumer_move_to_dlq() -> None:
    """Test moving failed event to Dead Letter Queue."""
    consumer = StreamConsumer()
    event = {
        "stream_name": "app.social.post.created",
        "message_id": "msg-12345",
        "service": "social",
        "event_type": "post.created",
        "payload": {"post_id": "p-1"},
        "retry_count": 5,
        "raw_data": {"post_id": "p-1"},
    }

    with (
        patch("stream_consumer.redis_client.add_to_dlq") as mock_add_dlq,
        patch("stream_consumer.redis_client.acknowledge_event") as mock_ack,
    ):
        mock_add_dlq.return_value = "dlq-msg-1"

        consumer.move_to_dlq(event, "Max retries exceeded")

        mock_add_dlq.assert_called_once()
        args, _ = mock_add_dlq.call_args
        assert args[0] == "app.dlq.social"
        assert args[1]["original_message_id"] == "msg-12345"
        assert args[1]["failure_reason"] == "Max retries exceeded"

        mock_ack.assert_called_once_with(
            stream_name="app.social.post.created",
            group_name="webhook-dispatcher",
            message_id="msg-12345",
        )


def test_webhook_manager_subscription_filtering() -> None:
    """Test webhook subscription filtering by event type, scope, author, and channel."""
    wm = WebhookManager()

    sub_scope = WebhookSubscription(
        id=uuid4(),
        service="social",
        target_url="https://example.com/1",
        secret="s1",
        events=["post.created"],
        filters={"scope": ["public"]},
    )
    assert wm._matches_subscription(sub_scope, "post.created", {"scope": "public"}) is True
    assert wm._matches_subscription(sub_scope, "post.created", {"scope": "private"}) is False
    assert wm._matches_subscription(sub_scope, "comment.created", {"scope": "public"}) is False

    sub_author = WebhookSubscription(
        id=uuid4(),
        service="social",
        target_url="https://example.com/2",
        secret="s2",
        events=["post.created"],
        filters={"authors": ["author-123", "author-456"]},
    )
    assert wm._matches_subscription(sub_author, "post.created", {"author_id": "author-123"}) is True
    assert wm._matches_subscription(sub_author, "post.created", {"author_id": "unknown"}) is False

    sub_channel = WebhookSubscription(
        id=uuid4(),
        service="messaging",
        target_url="https://example.com/3",
        secret="s3",
        events=["message.created"],
        filters={"channels": ["chan-1"]},
    )
    assert wm._matches_subscription(sub_channel, "message.created", {"channel_id": "chan-1"}) is True
    assert wm._matches_subscription(sub_channel, "message.created", {"channel_id": "chan-2"}) is False


def test_webhook_manager_cache_invalidation() -> None:
    """Test invalidation of cached webhook subscriptions."""
    wm = WebhookManager()
    wm._subscription_cache["subscriptions_social"] = [MagicMock()]
    wm._cache_timestamp = datetime.now(UTC)

    assert len(wm._subscription_cache) > 0
    wm.invalidate_cache()
    assert len(wm._subscription_cache) == 0
    assert wm._cache_timestamp is None


@pytest.mark.asyncio
async def test_event_processor_multi_subscription_tracking() -> None:
    """Test that event processor only acknowledges event when ALL subscriptions have completed."""
    processor = EventProcessor()

    sub1 = WebhookSubscription(
        id=uuid4(),
        service="social",
        target_url="https://example.com/sub1",
        secret="sec1",
        events=["post.created"],
        filters={},
    )
    sub2 = WebhookSubscription(
        id=uuid4(),
        service="social",
        target_url="https://example.com/sub2",
        secret="sec2",
        events=["post.created"],
        filters={},
    )

    event = {
        "stream_name": "app.social.post.created",
        "message_id": "msg-test-1",
        "service": "social",
        "event_type": "post.created",
        "payload": {"post_id": "p-1"},
        "retry_count": 0,
    }

    # Mock webhook_manager to return both subscriptions
    with (
        patch("event_processor.webhook_manager.find_matching_webhooks") as mock_find,
        patch("event_processor.webhook_delivery.deliver") as mock_deliver,
        patch("event_processor.stream_consumer.acknowledge_event") as mock_ack,
    ):
        mock_find.return_value = [(sub1, {"data": 1}), (sub2, {"data": 2})]

        # sub1 succeeds, sub2 fails with 500 (retryable)
        mock_deliver.side_effect = [
            DeliveryResult(True, 200, None, "del-1"),
            DeliveryResult(False, 500, "Server Error", "del-2"),
        ]

        await processor._process_event(event)

        # Event should NOT be acknowledged yet because sub2 is pending retry!
        mock_ack.assert_not_called()
        assert "msg-test-1" in processor.active_event_deliveries
        assert str(sub2.id) in processor.active_event_deliveries["msg-test-1"]["pending_sub_ids"]

        # Now execute the pending retry for sub2 with success
        retry_key = f"msg-test-1_{sub2.id}"
        assert retry_key in processor.pending_retries
        retry_info = processor.pending_retries[retry_key]

        mock_deliver.side_effect = [DeliveryResult(True, 200, None, "del-2")]
        await processor._execute_retry(retry_key, retry_info)

        # Now all subscriptions completed; event should be acknowledged!
        mock_ack.assert_called_once_with(event)
        assert "msg-test-1" not in processor.active_event_deliveries
