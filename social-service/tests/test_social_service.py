"""Comprehensive test suite for Social Service."""
from datetime import datetime
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from config import Settings, settings
from fastapi.testclient import TestClient
from models import Comment, Follow, IdempotencyKey, Post, Reaction, WebhookSubscription
from sqlalchemy.orm import Session
from utils import parse_user_id, utcnow


# --- 1. Settings & Config Tests ---

def test_settings_initialization():
    """Verify Settings loads properly with default values and property access."""
    s = Settings(database_url="postgresql://user:pass@localhost:5432/social")
    assert s.service_name == "social-service"
    assert "postgresql" in s.effective_database_url
    assert s.redis_url is not None


def test_effective_database_url_normalization():
    """Verify effective_database_url replaces postgres:// with postgresql://."""
    s = Settings(database_url="postgres://user:pass@localhost:5432/social")
    assert s.effective_database_url.startswith("postgresql://")


def test_parse_user_id_utility():
    """Verify parse_user_id parses UUID strings and converts Firebase UIDs deterministically."""
    # Native UUID
    sample_uuid = uuid4()
    assert parse_user_id(str(sample_uuid)) == sample_uuid
    assert parse_user_id(sample_uuid) == sample_uuid

    # Firebase UID
    firebase_uid = "firebase_user_abc_123"
    converted_1 = parse_user_id(firebase_uid)
    converted_2 = parse_user_id(firebase_uid)
    assert isinstance(converted_1, UUID)
    assert converted_1 == converted_2  # Deterministic


# --- 2. Health & Root Endpoints ---

def test_health_endpoint(client: TestClient):
    """GET /health should return 200 and healthy status."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy", "service": "social"}


def test_root_endpoint(client: TestClient):
    """GET / should return 200 and message."""
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "Social Service"


# --- 3. Internal Purge Endpoint ---

def test_internal_purge_unauthorized(client: TestClient):
    """POST /internal/users/{user_id}/purge without secret returns 403."""
    resp = client.post("/internal/users/test-user/purge")
    assert resp.status_code == 403


def test_internal_purge_authorized(client: TestClient, db_session: Session):
    """POST /internal/users/{user_id}/purge deletes all user records."""
    user_uid = str(uuid4())
    user_uuid = parse_user_id(user_uid)

    # Seed some user records
    post = Post(
        author_id=user_uuid,
        firebase_uid=user_uid,
        content="Post to be purged",
        scope="public",
        created_at=utcnow(),
    )
    db_session.add(post)
    db_session.commit()

    secret = "test-internal-secret"
    with patch.object(settings, "internal_gateway_secret", secret):
        resp = client.post(
            f"/internal/users/{user_uid}/purge",
            headers={"X-Internal-Secret": secret},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert resp.json()["deleted"] is True

    # Verify post was deleted
    found = db_session.query(Post).filter(Post.author_id == user_uuid).first()
    assert found is None


# --- 4. Posts API Endpoints ---

def test_create_post_missing_user_id(client: TestClient):
    """POST /social/posts without X-User-Id header returns 401."""
    resp = client.post(
        "/social/posts",
        json={"content": "Hello", "scope": "public"},
    )
    assert resp.status_code == 401


def test_create_post_invalid_scope(client: TestClient):
    """POST /social/posts with invalid scope returns 422."""
    user_id = str(uuid4())
    resp = client.post(
        "/social/posts",
        json={"content": "Hello", "scope": "unsupported_scope"},
        headers={"X-User-Id": user_id},
    )
    assert resp.status_code == 422


def test_create_and_get_post(client: TestClient):
    """POST /social/posts and GET /social/posts/{post_id}."""
    user_id = str(uuid4())
    payload = {
        "content": "This is a great workout session!",
        "scope": "public",
        "app_id": "workout-app",
        "attachments": [{"type": "image", "url": "https://example.com/img.png"}],
    }
    create_resp = client.post(
        "/social/posts",
        json=payload,
        headers={"X-User-Id": user_id},
    )
    assert create_resp.status_code == 201
    post_data = create_resp.json()
    post_id = post_data["id"]
    assert post_data["content"] == payload["content"]
    assert post_data["scope"] == "public"

    # Fetch post
    get_resp = client.get(
        f"/social/posts/{post_id}",
        headers={"X-User-Id": user_id},
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == post_id


def test_post_access_control_private(client: TestClient):
    """Private post should only be accessible by author."""
    author_id = str(uuid4())
    other_user_id = str(uuid4())

    create_resp = client.post(
        "/social/posts",
        json={"content": "Secret note", "scope": "private"},
        headers={"X-User-Id": author_id},
    )
    assert create_resp.status_code == 201
    post_id = create_resp.json()["id"]

    # Other user access denied
    get_resp = client.get(
        f"/social/posts/{post_id}",
        headers={"X-User-Id": other_user_id},
    )
    assert get_resp.status_code == 403


# --- 5. Comments & Reactions Endpoints ---

def test_comments_flow(client: TestClient):
    """Test creating comments, nested comments, and listing comments."""
    user_id = str(uuid4())
    post_resp = client.post(
        "/social/posts",
        json={"content": "Post with comments", "scope": "public"},
        headers={"X-User-Id": user_id},
    )
    post_id = post_resp.json()["id"]

    # 1. Create root comment
    c1_resp = client.post(
        f"/social/posts/{post_id}/comments",
        json={"content": "Nice workout!"},
        headers={"X-User-Id": user_id},
    )
    assert c1_resp.status_code == 201
    c1_data = c1_resp.json()
    c1_id = c1_data["id"]

    # 2. Create nested comment
    c2_resp = client.post(
        f"/social/posts/{post_id}/comments",
        json={"content": "Thanks!", "reply_to": c1_id},
        headers={"X-User-Id": user_id},
    )
    assert c2_resp.status_code == 201
    assert c2_resp.json()["reply_to"] == c1_id

    # 3. Get comments list
    list_resp = client.get(
        f"/social/posts/{post_id}/comments",
        headers={"X-User-Id": user_id},
    )
    assert list_resp.status_code == 200
    comments = list_resp.json()["comments"]
    assert len(comments) == 2


def test_toggle_reactions_flow(client: TestClient):
    """Test toggling reactions on and off."""
    user_id = str(uuid4())
    post_resp = client.post(
        "/social/posts",
        json={"content": "React to this", "scope": "public"},
        headers={"X-User-Id": user_id},
    )
    post_id = post_resp.json()["id"]

    # 1. React with 'like' -> creates
    r1 = client.post(
        f"/social/posts/{post_id}/reactions",
        json={"type": "like"},
        headers={"X-User-Id": user_id},
    )
    assert r1.status_code == 200
    assert r1.json()["action"] == "created"
    assert r1.json()["type"] == "like"

    # 2. React with 'like' again -> deletes (toggles off)
    r2 = client.post(
        f"/social/posts/{post_id}/reactions",
        json={"type": "like"},
        headers={"X-User-Id": user_id},
    )
    assert r2.status_code == 200
    assert r2.json()["action"] == "deleted"


# --- 6. Feed API Endpoints ---

def test_feed_home_and_user(client: TestClient):
    """Test feed retrieval with home and user scopes."""
    user1_id = str(uuid4())
    user2_id = str(uuid4())

    # User 1 creates public post
    client.post(
        "/social/posts",
        json={"content": "Public post by user 1", "scope": "public"},
        headers={"X-User-Id": user1_id},
    )

    # Home feed
    home_resp = client.get(
        "/social/posts?scope=home",
        headers={"X-User-Id": user2_id},
    )
    assert home_resp.status_code == 200
    assert "posts" in home_resp.json()
    assert len(home_resp.json()["posts"]) >= 1

    # User feed requires authors
    user_fail = client.get(
        "/social/posts?scope=user",
        headers={"X-User-Id": user2_id},
    )
    assert user_fail.status_code == 400

    # User feed with authors
    user_ok = client.get(
        f"/social/posts?scope=user&authors={user1_id}",
        headers={"X-User-Id": user2_id},
    )
    assert user_ok.status_code == 200
    assert len(user_ok.json()["posts"]) >= 1


# --- 7. Subscriptions & Follow Flow ---

def test_follow_and_unfollow(client: TestClient):
    """Test follow, idempotent follow, self-follow prevention, and unfollow."""
    follower = str(uuid4())
    followee = str(uuid4())

    # 1. Follow
    f1 = client.post(
        f"/social/follow/{followee}",
        headers={"X-User-Id": follower},
    )
    assert f1.status_code == 201
    assert f1.json()["action"] == "created"

    # 2. Idempotent follow
    f2 = client.post(
        f"/social/follow/{followee}",
        headers={"X-User-Id": follower},
    )
    assert f2.status_code == 201
    assert f2.json()["action"] == "created"

    # 3. Self-follow prevention
    f_self = client.post(
        f"/social/follow/{follower}",
        headers={"X-User-Id": follower},
    )
    assert f_self.status_code == 400

    # 4. List subscriptions
    subs = client.get(
        "/social/subscriptions",
        headers={"X-User-Id": follower},
    )
    assert subs.status_code == 200
    assert len(subs.json()["users"]) == 1

    # 5. List followers
    fol = client.get(
        "/social/followers",
        headers={"X-User-Id": followee},
    )
    assert fol.status_code == 200
    assert len(fol.json()["users"]) == 1

    # 6. Unfollow
    unf = client.delete(
        f"/social/follow/{followee}",
        headers={"X-User-Id": follower},
    )
    assert unf.status_code == 200
    assert unf.json()["action"] == "deleted"

    # 7. Unfollow when not following returns 404
    unf_again = client.delete(
        f"/social/follow/{followee}",
        headers={"X-User-Id": follower},
    )
    assert unf_again.status_code == 404


# --- 8. Webhook Subscriptions Endpoints ---

def test_webhook_subscriptions_crud(client: TestClient):
    """Test webhook subscription creation, listing, and deletion."""
    user_id = str(uuid4())

    # 1. Non-https rejected
    bad = client.post(
        "/social/webhooks/subscriptions",
        json={"target_url": "http://example.com/webhook", "events": ["post.created"]},
        headers={"X-User-Id": user_id},
    )
    assert bad.status_code == 422

    # 2. Create valid subscription
    create_resp = client.post(
        "/social/webhooks/subscriptions",
        json={
            "target_url": "https://example.com/webhook",
            "events": ["post.created", "comment.created"],
            "filters": {"scope": ["public"]},
        },
        headers={"X-User-Id": user_id},
    )
    assert create_resp.status_code == 201
    data = create_resp.json()
    sub_id = data["id"]
    assert data["service"] == "social"
    assert data["target_url"] == "https://example.com/webhook"
    assert len(data["secret"]) > 0

    # 3. List subscriptions
    list_resp = client.get(
        "/social/webhooks/subscriptions",
        headers={"X-User-Id": user_id},
    )
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1

    # 4. Get specific subscription
    get_resp = client.get(
        f"/social/webhooks/subscriptions/{sub_id}",
        headers={"X-User-Id": user_id},
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == sub_id

    # 5. Delete subscription
    del_resp = client.delete(
        f"/social/webhooks/subscriptions/{sub_id}",
        headers={"X-User-Id": user_id},
    )
    assert del_resp.status_code == 204

    # 6. Delete again returns 404
    del_again = client.delete(
        f"/social/webhooks/subscriptions/{sub_id}",
        headers={"X-User-Id": user_id},
    )
    assert del_again.status_code == 404


# --- 9. Idempotency Middleware Tests ---

def test_idempotency_cached_response(client: TestClient):
    """Same Idempotency-Key returns cached response without duplicate operations."""
    user_id = str(uuid4())
    idem_key = f"key-{uuid4()}"

    payload = {"content": "Idempotent post test", "scope": "public"}
    resp1 = client.post(
        "/social/posts",
        json=payload,
        headers={"X-User-Id": user_id, "Idempotency-Key": idem_key},
    )
    assert resp1.status_code == 201
    post1_id = resp1.json()["id"]

    # Second call with same key
    resp2 = client.post(
        "/social/posts",
        json=payload,
        headers={"X-User-Id": user_id, "Idempotency-Key": idem_key},
    )
    assert resp2.status_code == 201
    assert resp2.json()["id"] == post1_id  # Returns identical cached post
