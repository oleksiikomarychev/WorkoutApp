"""Tests for webhook subscription API."""

import pytest
from database import Base, get_db
from fastapi.testclient import TestClient
from main import app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_webhooks.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override get_db dependency
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Create test client
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """Create tables before each test and drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_create_webhook_subscription():
    """Test creating a webhook subscription."""
    response = client.post(
        "/social/webhooks/subscriptions",
        json={
            "target_url": "https://example.com/webhook",
            "events": ["post.created", "comment.created"],
            "filters": {"scope": ["public"]}
        },
        headers={"X-User-Id": "test-user-123"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["service"] == "social"
    assert data["target_url"] == "https://example.com/webhook"
    assert data["events"] == ["post.created", "comment.created"]
    assert data["filters"] == {"scope": ["public"]}
    assert data["active"] == "true"
    assert "secret" in data
    assert len(data["secret"]) > 0


def test_create_webhook_subscription_requires_https():
    """Test that webhook subscription requires HTTPS URL."""
    response = client.post(
        "/social/webhooks/subscriptions",
        json={
            "target_url": "http://example.com/webhook",
            "events": ["post.created"]
        },
        headers={"X-User-Id": "test-user-123"}
    )
    
    assert response.status_code == 422
    assert "https" in response.text.lower()


def test_create_webhook_subscription_requires_events():
    """Test that webhook subscription requires at least one event."""
    response = client.post(
        "/social/webhooks/subscriptions",
        json={
            "target_url": "https://example.com/webhook",
            "events": []
        },
        headers={"X-User-Id": "test-user-123"}
    )
    
    assert response.status_code == 422


def test_list_webhook_subscriptions():
    """Test listing webhook subscriptions."""
    # Create two subscriptions
    client.post(
        "/social/webhooks/subscriptions",
        json={
            "target_url": "https://example.com/webhook1",
            "events": ["post.created"]
        },
        headers={"X-User-Id": "test-user-123"}
    )
    
    client.post(
        "/social/webhooks/subscriptions",
        json={
            "target_url": "https://example.com/webhook2",
            "events": ["comment.created"]
        },
        headers={"X-User-Id": "test-user-123"}
    )
    
    # List all subscriptions
    response = client.get(
        "/social/webhooks/subscriptions",
        headers={"X-User-Id": "test-user-123"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["subscriptions"]) == 2


def test_get_webhook_subscription():
    """Test getting a specific webhook subscription."""
    # Create subscription
    create_response = client.post(
        "/social/webhooks/subscriptions",
        json={
            "target_url": "https://example.com/webhook",
            "events": ["post.created"]
        },
        headers={"X-User-Id": "test-user-123"}
    )
    
    subscription_id = create_response.json()["id"]
    
    # Get subscription
    response = client.get(
        f"/social/webhooks/subscriptions/{subscription_id}",
        headers={"X-User-Id": "test-user-123"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == subscription_id
    assert data["target_url"] == "https://example.com/webhook"


def test_get_nonexistent_webhook_subscription():
    """Test getting a non-existent webhook subscription."""
    response = client.get(
        "/social/webhooks/subscriptions/00000000-0000-0000-0000-000000000000",
        headers={"X-User-Id": "test-user-123"}
    )
    
    assert response.status_code == 404


def test_delete_webhook_subscription():
    """Test deleting a webhook subscription."""
    # Create subscription
    create_response = client.post(
        "/social/webhooks/subscriptions",
        json={
            "target_url": "https://example.com/webhook",
            "events": ["post.created"]
        },
        headers={"X-User-Id": "test-user-123"}
    )
    
    subscription_id = create_response.json()["id"]
    
    # Delete subscription
    response = client.delete(
        f"/social/webhooks/subscriptions/{subscription_id}",
        headers={"X-User-Id": "test-user-123"}
    )
    
    assert response.status_code == 204
    
    # Verify it's deleted
    get_response = client.get(
        f"/social/webhooks/subscriptions/{subscription_id}",
        headers={"X-User-Id": "test-user-123"}
    )
    
    assert get_response.status_code == 404


def test_delete_nonexistent_webhook_subscription():
    """Test deleting a non-existent webhook subscription."""
    response = client.delete(
        "/social/webhooks/subscriptions/00000000-0000-0000-0000-000000000000",
        headers={"X-User-Id": "test-user-123"}
    )
    
    assert response.status_code == 404


def test_filter_webhook_subscriptions_by_active():
    """Test filtering webhook subscriptions by active status."""
    # Create active subscription
    client.post(
        "/social/webhooks/subscriptions",
        json={
            "target_url": "https://example.com/webhook1",
            "events": ["post.created"]
        },
        headers={"X-User-Id": "test-user-123"}
    )
    
    # List active subscriptions
    response = client.get(
        "/social/webhooks/subscriptions?active=true",
        headers={"X-User-Id": "test-user-123"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert all(sub["active"] == "true" for sub in data["subscriptions"])


def test_test_webhook_delivery_nonexistent_subscription():
    """Test test delivery with non-existent subscription."""
    response = client.post(
        "/social/webhooks/test-delivery",
        json={
            "subscription_id": "00000000-0000-0000-0000-000000000000"
        },
        headers={"X-User-Id": "test-user-123"}
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
