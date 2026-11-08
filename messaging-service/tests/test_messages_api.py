"""Unit and integration tests for messages API endpoints."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from models import Channel, ChannelMember, Message
from sqlalchemy.orm import Session
from utils import firebase_uid_to_uuid


def test_send_message_empty_content_fails(client: TestClient) -> None:
    ch_id = str(uuid4())
    resp = client.post(
        f"/messaging/channels/{ch_id}/messages",
        json={"content": "   "},
        headers={"X-User-Id": "user-1"},
    )
    assert resp.status_code == 422


def test_send_message_invalid_channel_id(client: TestClient) -> None:
    resp = client.post(
        "/messaging/channels/not-a-uuid/messages",
        json={"content": "Hello!"},
        headers={"X-User-Id": "user-1"},
    )
    assert resp.status_code == 400
    assert "Invalid channel ID format" in resp.json()["detail"]


def test_send_message_success(client: TestClient, db_session: Session) -> None:
    ch_id = uuid4()
    user_id = "user-1"
    user_uuid = firebase_uid_to_uuid(user_id)

    channel = Channel(id=ch_id, type="group", name="General", channel_metadata={})
    member = ChannelMember(channel_id=ch_id, user_id=user_uuid)
    db_session.add_all([channel, member])
    db_session.commit()

    payload = {
        "content": "Hello team!",
        "kind": "text",
        "attachments": [],
    }

    resp = client.post(
        f"/messaging/channels/{ch_id}/messages",
        json=payload,
        headers={"X-User-Id": user_id},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["content"] == "Hello team!"
    assert data["channel_id"] == str(ch_id)


def test_get_messages_history(client: TestClient, db_session: Session) -> None:
    ch_id = uuid4()
    user_id = "user-1"
    user_uuid = firebase_uid_to_uuid(user_id)

    channel = Channel(id=ch_id, type="group", name="General", channel_metadata={})
    member = ChannelMember(channel_id=ch_id, user_id=user_uuid)
    msg = Message(
        id=uuid4(),
        channel_id=ch_id,
        sender_id=user_uuid,
        content="Test msg",
        kind="text",
        attachments=[],
    )
    db_session.add_all([channel, member, msg])
    db_session.commit()

    resp = client.get(
        f"/messaging/channels/{ch_id}/messages",
        headers={"X-User-Id": user_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["messages"]) == 1
    assert data["messages"][0]["content"] == "Test msg"
    assert data["has_more"] is False


def test_acknowledge_message_success_and_idempotency(client: TestClient, db_session: Session) -> None:
    msg_id = uuid4()
    ch_id = uuid4()
    user_id = "user-1"
    user_uuid = firebase_uid_to_uuid(user_id)

    channel = Channel(id=ch_id, type="group", name="General", channel_metadata={})
    member = ChannelMember(channel_id=ch_id, user_id=user_uuid)
    msg = Message(
        id=msg_id,
        channel_id=ch_id,
        sender_id=uuid4(),
        content="Hello",
        kind="text",
        attachments=[],
    )
    db_session.add_all([channel, member, msg])
    db_session.commit()

    # First ack
    resp = client.post(
        f"/messaging/messages/{msg_id}/ack",
        json={"status": "read"},
        headers={"X-User-Id": user_id},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["message_id"] == str(msg_id)
    assert data["status"] == "read"

    # Second ack (idempotent duplicate)
    resp2 = client.post(
        f"/messaging/messages/{msg_id}/ack",
        json={"status": "read"},
        headers={"X-User-Id": user_id},
    )
    assert resp2.status_code == 201
    assert resp2.json()["status"] == "read"
