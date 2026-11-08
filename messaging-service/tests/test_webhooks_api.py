"""Unit tests for webhooks API endpoints."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from models import WebhookSubscription
from sqlalchemy.orm import Session
from webhooks import generate_hmac_signature, generate_secret


def test_generate_secret_and_hmac() -> None:
    secret = generate_secret()
    assert len(secret) > 20

    payload = b'{"event":"test"}'
    sig1 = generate_hmac_signature(payload, secret)
    sig2 = generate_hmac_signature(payload, secret)
    assert sig1 == sig2
    assert len(sig1) == 64  # sha256 hex digest length


def test_create_webhook_subscription_requires_https(client: TestClient) -> None:
    payload = {
        "target_url": "http://insecure.com/webhook",
        "events": ["message.created"],
    }
    resp = client.post("/messaging/webhooks/subscriptions", json=payload)
    assert resp.status_code == 422


def test_create_webhook_subscription_success(client: TestClient, db_session: Session) -> None:
    payload = {
        "target_url": "https://secure.example.com/webhook",
        "events": ["message.created", "channel.created"],
    }

    resp = client.post("/messaging/webhooks/subscriptions", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["target_url"] == "https://secure.example.com/webhook"
    assert "message.created" in data["events"]
    assert data["service"] == "messaging"


def test_list_webhook_subscriptions(client: TestClient, db_session: Session) -> None:
    sub = WebhookSubscription(
        id=uuid4(),
        service="messaging",
        target_url="https://secure.example.com/webhook",
        secret="secret-123",
        events=["message.created"],
        filters={},
        active="true",
    )
    db_session.add(sub)
    db_session.commit()

    resp = client.get("/messaging/webhooks/subscriptions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["subscriptions"]) == 1
    assert data["subscriptions"][0]["target_url"] == "https://secure.example.com/webhook"
