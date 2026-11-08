"""Unit tests for messaging service models."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from models import (
    Channel,
    ChannelMember,
    IdempotencyKey,
    Message,
    MessageAcknowledgment,
    OutboxEvent,
    WebhookSubscription,
)


def test_channel_repr() -> None:
    ch_id = uuid4()
    channel = Channel(id=ch_id, type="group", name="General")
    assert repr(channel) == f"<Channel(id={ch_id}, type=group, name=General)>"


def test_channel_member_repr() -> None:
    ch_id = uuid4()
    u_id = uuid4()
    member = ChannelMember(channel_id=ch_id, user_id=u_id)
    assert repr(member) == f"<ChannelMember(channel_id={ch_id}, user_id={u_id})>"


def test_message_repr() -> None:
    m_id = uuid4()
    ch_id = uuid4()
    sender_id = uuid4()
    message = Message(id=m_id, channel_id=ch_id, sender_id=sender_id, kind="text")
    assert repr(message) == f"<Message(id={m_id}, channel_id={ch_id}, sender_id={sender_id}, kind=text)>"


def test_message_acknowledgment_repr() -> None:
    m_id = uuid4()
    u_id = uuid4()
    ack = MessageAcknowledgment(message_id=m_id, user_id=u_id, status="read")
    assert repr(ack) == f"<MessageAcknowledgment(message_id={m_id}, user_id={u_id}, status=read)>"


def test_idempotency_key_repr() -> None:
    u_id = uuid4()
    key = IdempotencyKey(key="k-1", user_id=u_id, endpoint="/test")
    assert repr(key) == f"<IdempotencyKey(key=k-1, user_id={u_id}, endpoint=/test)>"


def test_outbox_event_repr() -> None:
    e_id = uuid4()
    event_pending = OutboxEvent(id=e_id, event_type="message.created", published_at=None)
    assert repr(event_pending) == f"<OutboxEvent(id={e_id}, event_type=message.created, status=pending)>"

    event_published = OutboxEvent(id=e_id, event_type="message.created", published_at=datetime.utcnow())
    assert repr(event_published) == f"<OutboxEvent(id={e_id}, event_type=message.created, status=published)>"


def test_webhook_subscription_repr() -> None:
    sub_id = uuid4()
    sub = WebhookSubscription(id=sub_id, service="messaging", target_url="https://example.com/wh", active="true")
    assert repr(sub) == (
        f"<WebhookSubscription(id={sub_id}, service=messaging, target_url=https://example.com/wh, active=true)>"
    )
