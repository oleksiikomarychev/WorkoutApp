"""Unit and integration tests for channels API endpoints."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from models import Channel, ChannelMember
from sqlalchemy.orm import Session
from utils import firebase_uid_to_uuid


def test_create_channel_validation_direct_requires_two_members(client: TestClient) -> None:
    payload = {
        "type": "direct",
        "members": ["user-1", "user-2", "user-3"],
    }
    resp = client.post("/messaging/channels", json=payload, headers={"X-User-Id": "user-1"})
    assert resp.status_code == 422


def test_create_channel_validation_group_requires_name(client: TestClient) -> None:
    payload = {
        "type": "group",
        "members": ["user-1", "user-2"],
    }
    resp = client.post("/messaging/channels", json=payload, headers={"X-User-Id": "user-1"})
    assert resp.status_code == 422


def test_create_channel_validation_duplicate_members(client: TestClient) -> None:
    payload = {
        "type": "group",
        "name": "Team",
        "members": ["user-1", "user-1"],
    }
    resp = client.post("/messaging/channels", json=payload, headers={"X-User-Id": "user-1"})
    assert resp.status_code == 422


def test_create_channel_success(client: TestClient) -> None:
    creator_id = "creator-uid"
    peer_id = "peer-uid"

    payload = {
        "type": "direct",
        "members": [creator_id, peer_id],
    }

    resp = client.post("/messaging/channels", json=payload, headers={"X-User-Id": creator_id})
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "direct"
    assert len(data["members"]) == 2


def test_get_channel_not_found(client: TestClient) -> None:
    ch_id = str(uuid4())
    resp = client.get(f"/messaging/channels/{ch_id}", headers={"X-User-Id": "user-1"})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Channel not found"


def test_get_channel_not_member(client: TestClient, db_session: Session) -> None:
    ch_id = uuid4()
    channel = Channel(id=ch_id, type="group", name="General", channel_metadata={})
    db_session.add(channel)
    db_session.commit()

    resp = client.get(f"/messaging/channels/{ch_id}", headers={"X-User-Id": "outsider"})
    assert resp.status_code == 403
    assert "not a member" in resp.json()["detail"]


def test_manage_members_leave_channel(client: TestClient, db_session: Session) -> None:
    ch_id = uuid4()
    user_id = "user-123"
    user_uuid = firebase_uid_to_uuid(user_id)

    channel = Channel(id=ch_id, type="group", name="General", channel_metadata={})
    member = ChannelMember(channel_id=ch_id, user_id=user_uuid)
    db_session.add_all([channel, member])
    db_session.commit()

    resp = client.post(
        f"/messaging/channels/{ch_id}/members",
        json={"operation": "leave"},
        headers={"X-User-Id": user_id},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Left channel successfully"

    # Verify left_at is set in database
    db_member = (
        db_session.query(ChannelMember)
        .filter(
            ChannelMember.channel_id == ch_id,
            ChannelMember.user_id == user_uuid,
        )
        .first()
    )
    assert db_member is not None
    assert db_member.left_at is not None
