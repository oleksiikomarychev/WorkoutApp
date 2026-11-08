"""Unit tests for presence operations and endpoints."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from models import Channel, ChannelMember
from presence import (
    get_multiple_user_presence,
    get_user_presence,
    set_user_presence,
)
from sqlalchemy.orm import Session
from utils import firebase_uid_to_uuid


def test_set_and_get_user_presence() -> None:
    u_id = uuid4()
    mock_redis = MagicMock()
    mock_redis.get.return_value = json.dumps({"status": "online", "last_seen": "2026-10-09T00:00:00Z"})

    with patch("presence.get_redis_client", return_value=mock_redis):
        assert set_user_presence(u_id, "online") is True
        mock_redis.setex.assert_called_once()

        presence = get_user_presence(u_id)
        assert presence is not None
        assert presence["status"] == "online"


def test_get_multiple_user_presence() -> None:
    u1, u2 = uuid4(), uuid4()
    mock_redis = MagicMock()
    pipe_mock = MagicMock()
    pipe_mock.execute.return_value = [
        json.dumps({"status": "online", "last_seen": "2026-10-09T00:00:00Z"}),
        None,
    ]
    mock_redis.pipeline.return_value = pipe_mock

    with patch("presence.get_redis_client", return_value=mock_redis):
        res = get_multiple_user_presence([u1, u2])
        assert res[str(u1)]["status"] == "online"
        assert res[str(u2)] is None


def test_presence_api_endpoint_with_firebase_uid(client: TestClient, db_session: Session) -> None:
    user_uid = "fb-user-123"
    user_uuid = firebase_uid_to_uuid(user_uid)
    target_uuid = uuid4()

    ch_id = uuid4()
    channel = Channel(id=ch_id, type="group", name="General", channel_metadata={})
    m1 = ChannelMember(channel_id=ch_id, user_id=user_uuid)
    m2 = ChannelMember(channel_id=ch_id, user_id=target_uuid)
    db_session.add_all([channel, m1, m2])
    db_session.commit()

    with patch(
        "presence_api.get_multiple_user_presence",
        return_value={str(target_uuid): {"status": "online", "last_seen": "2026-10-09T00:00:00Z"}},
    ):
        response = client.get("/messaging/presence", headers={"X-User-Id": user_uid})
        assert response.status_code == 200
        data = response.json()
        assert len(data["presence"]) == 1
        assert data["presence"][0]["user_id"] == str(target_uuid)
        assert data["presence"][0]["status"] == "online"
