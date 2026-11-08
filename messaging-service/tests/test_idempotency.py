"""Unit tests for idempotency middleware and functions."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import Request, Response
from idempotency import IdempotencyMiddleware
from models import IdempotencyKey
from utils import firebase_uid_to_uuid


@pytest.mark.asyncio
async def test_idempotency_non_post_passes_through() -> None:
    app_mock = MagicMock()
    middleware = IdempotencyMiddleware(app_mock)

    request = MagicMock(spec=Request)
    request.method = "GET"
    call_next = AsyncMock(return_value=Response(content=b"ok", status_code=200))

    resp = await middleware.dispatch(request, call_next)
    assert resp.status_code == 200
    call_next.assert_called_once()


@pytest.mark.asyncio
async def test_idempotency_without_header_passes_through() -> None:
    app_mock = MagicMock()
    middleware = IdempotencyMiddleware(app_mock)

    request = MagicMock(spec=Request)
    request.method = "POST"
    request.headers = {}
    call_next = AsyncMock(return_value=Response(content=b"ok", status_code=200))

    resp = await middleware.dispatch(request, call_next)
    assert resp.status_code == 200
    call_next.assert_called_once()


@pytest.mark.asyncio
async def test_idempotency_returns_cached_response_and_conflict() -> None:
    app_mock = MagicMock()
    middleware = IdempotencyMiddleware(app_mock)

    user_raw = "test-user-123"
    user_uuid = firebase_uid_to_uuid(user_raw)
    idempotency_key = "idem-key-abc"

    existing_record = IdempotencyKey(
        key=idempotency_key,
        service="messaging-service",
        endpoint="/messaging/channels",
        user_id=user_uuid,
        response_status=201,
        response_body={"id": "channel-1", "name": "General"},
    )

    # 1. Matching request returns cached response
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = existing_record

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("idempotency.SessionLocal", lambda: mock_db)

        request = MagicMock(spec=Request)
        request.method = "POST"
        request.headers = {"Idempotency-Key": idempotency_key, "X-User-Id": user_raw}
        request.url.path = "/messaging/channels"
        call_next = AsyncMock()

        resp = await middleware.dispatch(request, call_next)
        assert resp.status_code == 201
        assert json.loads(resp.body.decode("utf-8")) == {"id": "channel-1", "name": "General"}
        call_next.assert_not_called()

    # 2. Conflicting endpoint returns 409
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("idempotency.SessionLocal", lambda: mock_db)

        request_conflict = MagicMock(spec=Request)
        request_conflict.method = "POST"
        request_conflict.headers = {"Idempotency-Key": idempotency_key, "X-User-Id": user_raw}
        request_conflict.url.path = "/messaging/other-endpoint"
        call_next = AsyncMock()

        resp_conflict = await middleware.dispatch(request_conflict, call_next)
        assert resp_conflict.status_code == 409
        data = json.loads(resp_conflict.body.decode("utf-8"))
        assert data["error"]["code"] == "IDEMPOTENCY_KEY_CONFLICT"
