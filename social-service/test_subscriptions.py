"""Tests for subscriptions API endpoints."""
from uuid import uuid4

import pytest
from database import Base, get_db
from fastapi.testclient import TestClient
from main import app
from models import Follow, OutboxEvent
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Setup test database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """Create tables before each test and drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_follow_user_success():
    """Test successfully following a user."""
    follower_id = str(uuid4())
    followee_id = str(uuid4())
    
    response = client.post(
        f"/social/follow/{followee_id}",
        headers={"X-User-Id": follower_id}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["follower_id"] == follower_id
    assert data["followee_id"] == followee_id
    assert data["action"] == "created"
    assert "created_at" in data
    
    # Verify follow was created in database
    db = TestingSessionLocal()
    follow = db.query(Follow).filter(
        Follow.follower_id == follower_id,
        Follow.followee_id == followee_id
    ).first()
    assert follow is not None
    
    # Verify outbox event was created
    event = db.query(OutboxEvent).filter(
        OutboxEvent.stream_name == "app.social.follow.changed"
    ).first()
    assert event is not None
    assert event.event_type == "follow.changed"
    assert event.payload["action"] == "created"
    assert event.payload["follower_id"] == follower_id
    assert event.payload["followee_id"] == followee_id
    
    db.close()


def test_follow_user_idempotent():
    """Test that following the same user twice is idempotent."""
    follower_id = str(uuid4())
    followee_id = str(uuid4())
    
    # First follow
    response1 = client.post(
        f"/social/follow/{followee_id}",
        headers={"X-User-Id": follower_id}
    )
    assert response1.status_code == 201
    
    # Second follow (should be idempotent)
    response2 = client.post(
        f"/social/follow/{followee_id}",
        headers={"X-User-Id": follower_id}
    )
    assert response2.status_code == 201
    assert response1.json()["follower_id"] == response2.json()["follower_id"]
    assert response1.json()["followee_id"] == response2.json()["followee_id"]
    
    # Verify only one follow exists in database
    db = TestingSessionLocal()
    follow_count = db.query(Follow).filter(
        Follow.follower_id == follower_id,
        Follow.followee_id == followee_id
    ).count()
    assert follow_count == 1
    db.close()


def test_follow_user_self_follow_prevented():
    """Test that users cannot follow themselves."""
    user_id = str(uuid4())
    
    response = client.post(
        f"/social/follow/{user_id}",
        headers={"X-User-Id": user_id}
    )
    
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "SELF_FOLLOW_NOT_ALLOWED"


def test_follow_user_missing_user_id():
    """Test that X-User-Id header is required."""
    followee_id = str(uuid4())
    
    response = client.post(f"/social/follow/{followee_id}")
    
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "MISSING_USER_ID"


def test_unfollow_user_success():
    """Test successfully unfollowing a user."""
    follower_id = str(uuid4())
    followee_id = str(uuid4())
    
    # First, create a follow relationship
    client.post(
        f"/social/follow/{followee_id}",
        headers={"X-User-Id": follower_id}
    )
    
    # Now unfollow
    response = client.delete(
        f"/social/follow/{followee_id}",
        headers={"X-User-Id": follower_id}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["follower_id"] == follower_id
    assert data["followee_id"] == followee_id
    assert data["action"] == "deleted"
    
    # Verify follow was deleted from database
    db = TestingSessionLocal()
    follow = db.query(Follow).filter(
        Follow.follower_id == follower_id,
        Follow.followee_id == followee_id
    ).first()
    assert follow is None
    
    # Verify outbox event was created for deletion
    events = db.query(OutboxEvent).filter(
        OutboxEvent.stream_name == "app.social.follow.changed"
    ).all()
    assert len(events) == 2  # One for create, one for delete
    delete_event = events[1]
    assert delete_event.payload["action"] == "deleted"
    
    db.close()


def test_unfollow_user_not_following():
    """Test unfollowing a user that is not being followed."""
    follower_id = str(uuid4())
    followee_id = str(uuid4())
    
    response = client.delete(
        f"/social/follow/{followee_id}",
        headers={"X-User-Id": follower_id}
    )
    
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "FOLLOW_NOT_FOUND"


def test_get_subscriptions_success():
    """Test getting list of subscriptions."""
    follower_id = str(uuid4())
    followee1_id = str(uuid4())
    followee2_id = str(uuid4())
    followee3_id = str(uuid4())
    
    # Create multiple follow relationships
    client.post(f"/social/follow/{followee1_id}", headers={"X-User-Id": follower_id})
    client.post(f"/social/follow/{followee2_id}", headers={"X-User-Id": follower_id})
    client.post(f"/social/follow/{followee3_id}", headers={"X-User-Id": follower_id})
    
    # Get subscriptions
    response = client.get(
        "/social/subscriptions",
        headers={"X-User-Id": follower_id}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["users"]) == 3
    assert data["has_more"] is False
    assert data["cursor"] is None
    
    # Verify all followees are in the list
    user_ids = [user["user_id"] for user in data["users"]]
    assert followee1_id in user_ids
    assert followee2_id in user_ids
    assert followee3_id in user_ids


def test_get_subscriptions_pagination():
    """Test pagination of subscriptions list."""
    follower_id = str(uuid4())
    
    # Create 5 follow relationships
    followee_ids = [str(uuid4()) for _ in range(5)]
    for followee_id in followee_ids:
        client.post(f"/social/follow/{followee_id}", headers={"X-User-Id": follower_id})
    
    # Get first page with limit 2
    response = client.get(
        "/social/subscriptions?limit=2",
        headers={"X-User-Id": follower_id}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["users"]) == 2
    assert data["has_more"] is True
    assert data["cursor"] is not None
    
    # Get second page using cursor
    response2 = client.get(
        f"/social/subscriptions?limit=2&cursor={data['cursor']}",
        headers={"X-User-Id": follower_id}
    )
    
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2["users"]) == 2
    assert data2["has_more"] is True


def test_get_followers_success():
    """Test getting list of followers."""
    followee_id = str(uuid4())
    follower1_id = str(uuid4())
    follower2_id = str(uuid4())
    follower3_id = str(uuid4())
    
    # Create multiple follow relationships
    client.post(f"/social/follow/{followee_id}", headers={"X-User-Id": follower1_id})
    client.post(f"/social/follow/{followee_id}", headers={"X-User-Id": follower2_id})
    client.post(f"/social/follow/{followee_id}", headers={"X-User-Id": follower3_id})
    
    # Get followers
    response = client.get(
        "/social/followers",
        headers={"X-User-Id": followee_id}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["users"]) == 3
    assert data["has_more"] is False
    assert data["cursor"] is None
    
    # Verify all followers are in the list
    user_ids = [user["user_id"] for user in data["users"]]
    assert follower1_id in user_ids
    assert follower2_id in user_ids
    assert follower3_id in user_ids


def test_get_followers_empty():
    """Test getting followers when user has no followers."""
    user_id = str(uuid4())
    
    response = client.get(
        "/social/followers",
        headers={"X-User-Id": user_id}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["users"]) == 0
    assert data["has_more"] is False


def test_subscriptions_empty():
    """Test getting subscriptions when user follows no one."""
    user_id = str(uuid4())
    
    response = client.get(
        "/social/subscriptions",
        headers={"X-User-Id": user_id}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["users"]) == 0
    assert data["has_more"] is False
