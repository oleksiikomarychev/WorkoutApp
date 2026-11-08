"""Unit and integration tests for accounts-service."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import grpc
import pytest
from accounts_service import schemas
from accounts_service.config import Settings, get_settings, settings
from accounts_service.dependencies import get_current_user_id, get_db
from accounts_service.grpc_server import (
    AccountsServicer,
    HealthServicer,
    accounts_pb2,
    common_pb2,
    health_pb2,
)
from accounts_service.main import app
from accounts_service.models import UnitSystem, UserAvatar, UserCoachingProfile, UserProfile, UserSettings
from accounts_service.services import profile_service, users_service
from fastapi import HTTPException
from fastapi.testclient import TestClient

# --- 1. Settings & Config Tests ---

def test_settings_initialization():
    """Verify Settings loads properly with default values."""
    s = Settings()
    assert s.ACCOUNTS_GRPC_PORT == 50055
    assert s.ACCOUNTS_DATABASE_URL is not None
    assert get_settings() is not None


# --- 2. Schemas & Models Tests ---

def test_unit_system_enum():
    """Verify UnitSystem StrEnum values."""
    assert UnitSystem.METRIC == "metric"
    assert UnitSystem.IMPERIAL == "imperial"


def test_schema_validations():
    """Verify input validation on profile update schemas."""
    # Negative bodyweight should fail validation
    with pytest.raises(Exception):
        schemas.ProfileUpdateRequest(bodyweight_kg=-5.0)

    # Negative height should fail validation
    with pytest.raises(Exception):
        schemas.ProfileUpdateRequest(height_cm=-10.0)

    # Negative age should fail validation
    with pytest.raises(Exception):
        schemas.ProfileUpdateRequest(age=-1)

    # Age > 150 should fail validation
    with pytest.raises(Exception):
        schemas.ProfileUpdateRequest(age=200)

    # Rating > 5.0 should fail validation
    with pytest.raises(Exception):
        schemas.CoachingRatingUpdate(average_rating=6.0)

    # Valid profile update request
    req = schemas.ProfileUpdateRequest(display_name="Alex", age=30, bodyweight_kg=75.5)
    assert req.display_name == "Alex"
    assert req.age == 30


# --- 3. Profile Service Helper Tests ---

def test_parse_unit_system():
    """Verify parsing and validation of unit system strings."""
    assert profile_service.parse_unit_system("metric") == UnitSystem.METRIC
    assert profile_service.parse_unit_system("imperial") == UnitSystem.IMPERIAL
    assert profile_service.parse_unit_system(" METRIC ") == UnitSystem.METRIC
    assert profile_service.parse_unit_system("Imperial") == UnitSystem.IMPERIAL
    assert profile_service.parse_unit_system(None) is None

    with pytest.raises(HTTPException) as exc_info:
        profile_service.parse_unit_system("unknown")
    assert exc_info.value.status_code == 400


def test_build_coaching_response():
    """Verify mapping of UserCoachingProfile entity to CoachingProfileResponse schema."""
    assert profile_service.build_coaching_response(None) is None

    now = datetime.now(UTC)
    coaching = UserCoachingProfile(
        user_id="user_123",
        enabled=True,
        tagline="Elite Strength Coach",
        description="10 years experience",
        specializations=["powerlifting", "hypertrophy"],
        languages=["en", "es"],
        rate_amount_minor=5000,
        stripe_connect_account_id="acct_123",
        created_at=now,
        updated_at=now,
    )
    resp = profile_service.build_coaching_response(coaching)
    assert resp is not None
    assert resp.enabled is True
    assert resp.tagline == "Elite Strength Coach"
    assert resp.specializations == ["powerlifting", "hypertrophy"]
    assert resp.rate_plan is not None
    assert resp.rate_plan.amount_minor == 5000


def test_build_profile_response():
    """Verify mapping of ProfileData domain object to ProfileResponse schema."""
    now = datetime.now(UTC)
    prof = UserProfile(
        user_id="u1",
        display_name="Tester",
        bio="Hello world",
        photo_url="https://example.com/p.png",
        bodyweight_kg=80.0,
        height_cm=180.0,
        age=25,
        sex="male",
        training_experience_years=3.5,
        training_experience_level="intermediate",
        primary_default_goal="strength",
        training_environment="gym",
        weekly_gain_coef=1.0,
        last_active_at=now,
        is_public=True,
        created_at=now,
        updated_at=now,
    )
    settings_obj = UserSettings(
        user_id="u1",
        unit_system=UnitSystem.METRIC,
        locale="en",
        timezone="UTC",
        notifications_enabled=True,
        created_at=now,
        updated_at=now,
    )
    data = profile_service.ProfileData(profile=prof, settings=settings_obj)
    resp = profile_service.build_profile_response(data)

    assert resp.user_id == "u1"
    assert resp.display_name == "Tester"
    assert resp.settings.unit_system == "metric"
    assert resp.settings.locale == "en"
    assert resp.coaching is None


@pytest.mark.asyncio
async def test_ensure_profile_and_settings_soft_deleted():
    """Verify that soft-deleted users raise 410 GONE."""
    now = datetime.now(UTC)
    deleted_profile = UserProfile(user_id="deleted_user", display_name="deleted:abc", deleted_at=now)

    mock_db = AsyncMock()
    mock_db.get.side_effect = lambda model, uid: deleted_profile if model == UserProfile else None

    with pytest.raises(HTTPException) as exc_info:
        await profile_service.ensure_profile_and_settings(mock_db, "deleted_user")
    assert exc_info.value.status_code == 410


@pytest.mark.asyncio
async def test_ensure_coaching_profile_missing_user():
    """Verify that ensure_coaching_profile raises 404 when UserProfile does not exist."""
    mock_db = AsyncMock()
    mock_db.get.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await profile_service.ensure_coaching_profile(mock_db, "nonexistent")
    assert exc_info.value.status_code == 404


# --- 4. Users Service Logic Tests ---

@pytest.mark.asyncio
async def test_users_service_list_users_queries():
    """Verify list_users builds query without duplicate join when sorting by rating."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.unique.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result

    # Coach=True and sort_by="rating" must not crash or duplicate table join
    users = await users_service.list_users(
        mock_db,
        coach=True,
        sort_by="rating",
        specializations=["powerlifting"],
        min_rate=1000,
        max_rate=5000,
    )
    assert users == []
    assert mock_db.execute.called


@pytest.mark.asyncio
async def test_users_service_get_users_by_ids_empty():
    """Verify get_users_by_ids short-circuits on empty list."""
    mock_db = AsyncMock()
    result = await users_service.get_users_by_ids(mock_db, [])
    assert result == []
    assert not mock_db.execute.called


# --- 5. HTTP Endpoints Tests (FastAPI TestClient) ---

@pytest.fixture
def test_client():
    """Create a FastAPI TestClient with mocked dependencies."""
    now = datetime.now(UTC)
    sample_profile = UserProfile(
        user_id="test_user_id",
        display_name="Test User",
        bio="Test Bio",
        photo_url=None,
        bodyweight_kg=75.0,
        height_cm=175.0,
        age=28,
        sex="other",
        training_experience_years=2.0,
        training_experience_level="beginner",
        primary_default_goal="general_fitness",
        training_environment="home",
        weekly_gain_coef=0.5,
        last_active_at=now,
        is_public=True,
        created_at=now,
        updated_at=now,
    )
    sample_settings = UserSettings(
        user_id="test_user_id",
        unit_system=UnitSystem.METRIC,
        locale="en",
        timezone="Europe/Kyiv",
        notifications_enabled=True,
        created_at=now,
        updated_at=now,
    )

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.get.side_effect = lambda model, uid: (
        sample_profile if model == UserProfile else (sample_settings if model == UserSettings else None)
    )

    app.dependency_overrides[get_current_user_id] = lambda: "test_user_id"
    app.dependency_overrides[get_db] = lambda: mock_db

    client = TestClient(app, raise_server_exceptions=False)
    yield client, mock_db, sample_profile, sample_settings

    app.dependency_overrides.clear()


def test_health_endpoint(test_client):
    """Verify GET /health returns 200 OK."""
    client, _, _, _ = test_client
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_get_profile_me(test_client):
    """Verify GET /profile/me returns current user profile."""
    client, _, profile, settings_obj = test_client
    resp = client.get("/profile/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "test_user_id"
    assert data["display_name"] == "Test User"
    assert data["settings"]["unit_system"] == "metric"


def test_update_profile_me(test_client):
    """Verify PATCH /profile/me updates user attributes."""
    client, mock_db, profile, _ = test_client
    payload = {"display_name": "Updated Name", "bio": "New bio", "bodyweight_kg": 76.5}
    resp = client.patch("/profile/me", json=payload)
    assert resp.status_code == 200
    assert profile.display_name == "Updated Name"
    assert profile.bio == "New bio"
    assert profile.bodyweight_kg == 76.5


def test_update_profile_me_empty_display_name(test_client):
    """Verify PATCH /profile/me rejects empty display_name with 400."""
    client, _, _, _ = test_client
    resp = client.patch("/profile/me", json={"display_name": "   "})
    assert resp.status_code == 400
    assert "display_name must not be empty" in resp.json()["detail"]


def test_get_and_patch_settings(test_client):
    """Verify GET and PATCH /profile/settings."""
    client, _, _, settings_obj = test_client
    # GET settings
    resp = client.get("/profile/settings")
    assert resp.status_code == 200
    assert resp.json()["unit_system"] == "metric"

    # PATCH settings
    resp2 = client.patch(
        "/profile/settings",
        json={"unit_system": "imperial", "locale": "uk", "notifications_enabled": False},
    )
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["unit_system"] == "imperial"
    assert data["locale"] == "uk"
    assert data["notifications_enabled"] is False


def test_get_profile_by_id(test_client):
    """Verify GET /profile/{user_id}."""
    client, _, _, _ = test_client
    resp = client.get("/profile/test_user_id")
    assert resp.status_code == 200
    assert resp.json()["user_id"] == "test_user_id"


def test_update_coaching_rating_crm(test_client):
    """Verify internal PATCH /profile/{user_id}/coaching called by CRM service."""
    client, mock_db, _, _ = test_client
    resp = client.patch(
        "/profile/test_user_id/coaching",
        json={"average_rating": 4.8, "review_count": 12},
    )
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_users_endpoints(test_client):
    """Verify GET /users/all and GET /users."""
    client, mock_db, profile, _ = test_client

    mock_result = MagicMock()
    mock_result.scalars.return_value.unique.return_value.all.return_value = [profile]
    mock_db.execute.return_value = mock_result

    # GET /users/all
    resp_all = client.get("/users/all?coach=false&limit=10")
    assert resp_all.status_code == 200
    assert len(resp_all.json()) == 1
    assert resp_all.json()[0]["user_id"] == "test_user_id"

    # GET /users with comma-separated list
    resp_list = client.get("/users?user_ids=test_user_id,other_user")
    assert resp_list.status_code == 200
    assert len(resp_list.json()) == 1

    # GET /users with empty user_ids
    resp_empty = client.get("/users?user_ids= , ")
    assert resp_empty.status_code == 200
    assert resp_empty.json() == []


def test_avatars_endpoints(test_client):
    """Verify avatar application and retrieval."""
    client, mock_db, _, _ = test_client

    # Apply avatar empty
    resp_empty = client.post("/avatars/apply", content=b"")
    assert resp_empty.status_code == 400

    # Apply avatar too small (<16 bytes)
    resp_small = client.post("/avatars/apply", content=b"short")
    assert resp_small.status_code == 400

    # Apply avatar valid
    dummy_image = b"RIFF....WEBPVP8 ......" + b"0" * 32
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    resp_valid = client.post(
        "/avatars/apply",
        content=dummy_image,
        headers={"Content-Type": "image/webp"},
    )
    assert resp_valid.status_code == 200
    assert resp_valid.json() == {"uid": "test_user_id", "ok": True}

    # Get avatar not found
    mock_result_empty = MagicMock()
    mock_result_empty.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result_empty
    resp_get_404 = client.get("/avatars/unknown.png")
    assert resp_get_404.status_code == 404

    # Get avatar found
    mock_avatar = UserAvatar(user_id="u1", image=dummy_image, content_type="image/png")
    mock_result_found = MagicMock()
    mock_result_found.scalar_one_or_none.return_value = mock_avatar
    mock_db.execute.return_value = mock_result_found
    resp_get_found = client.get("/avatars/u1.png")
    assert resp_get_found.status_code == 200
    assert resp_get_found.headers["content-type"] == "image/png"
    assert resp_get_found.content == dummy_image


def test_internal_purge_endpoint(test_client):
    """Verify /internal/users/{user_id}/purge authentication and execution."""
    client, mock_db, _, _ = test_client

    with patch.object(settings, "INTERNAL_GATEWAY_SECRET", "super-secret"):
        # Without secret header
        resp_no_secret = client.post("/internal/users/target_user/purge")
        assert resp_no_secret.status_code == 403

        # With wrong secret
        resp_wrong = client.post(
            "/internal/users/target_user/purge",
            headers={"X-Internal-Secret": "wrong"},
        )
        assert resp_wrong.status_code == 403

        # With correct secret
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_res

        resp_ok = client.post(
            "/internal/users/target_user/purge",
            headers={"X-Internal-Secret": "super-secret"},
        )
        assert resp_ok.status_code == 200
        assert resp_ok.json() == {"status": "ok"}


# --- 6. gRPC Servicer Tests ---

@pytest.mark.asyncio
async def test_grpc_get_profile():
    """Verify gRPC GetProfile endpoint."""
    servicer = AccountsServicer()
    context = MagicMock()

    # Missing user_context
    req_no_ctx = accounts_pb2.GetProfileRequest()
    res_no_ctx = await servicer.GetProfile(req_no_ctx, context)
    context.set_code.assert_called_with(grpc.StatusCode.INVALID_ARGUMENT)
    assert not res_no_ctx.HasField("profile")

    # Valid profile request
    now = datetime.now(UTC)
    prof = UserProfile(user_id="grpc_user", display_name="GRPC User", is_public=True, created_at=now, updated_at=now)
    settings_obj = UserSettings(
        user_id="grpc_user",
        unit_system=UnitSystem.METRIC,
        locale="en",
        created_at=now,
        updated_at=now,
    )
    data = profile_service.ProfileData(profile=prof, settings=settings_obj)

    mock_db = AsyncMock()
    mock_db.add = MagicMock()

    async def mock_get_db():
        yield mock_db

    with (
        patch("accounts_service.grpc_server.get_db", mock_get_db),
        patch("accounts_service.grpc_server.ensure_profile_and_settings", new_callable=AsyncMock) as mock_ensure,
    ):
        mock_ensure.return_value = data
        req_valid = accounts_pb2.GetProfileRequest(
            user_context=common_pb2.UserContext(user_id="grpc_user")
        )
        res_valid = await servicer.GetProfile(req_valid, context)
        assert res_valid.profile.user_id == "grpc_user"
        assert res_valid.profile.name == "GRPC User"
        assert res_valid.profile.preferences["unit_system"] == "metric"


@pytest.mark.asyncio
async def test_grpc_update_profile():
    """Verify gRPC UpdateProfile endpoint."""
    servicer = AccountsServicer()
    context = MagicMock()

    # Missing user_context
    req_no_ctx = accounts_pb2.UpdateProfileRequest()
    await servicer.UpdateProfile(req_no_ctx, context)
    context.set_code.assert_called_with(grpc.StatusCode.INVALID_ARGUMENT)

    # Valid update
    now = datetime.now(UTC)
    prof = UserProfile(user_id="grpc_user", display_name="Old", is_public=True, created_at=now, updated_at=now)
    settings_obj = UserSettings(
        user_id="grpc_user",
        unit_system=UnitSystem.METRIC,
        locale="en",
        created_at=now,
        updated_at=now,
    )
    data = profile_service.ProfileData(profile=prof, settings=settings_obj)

    mock_db = AsyncMock()
    mock_db.add = MagicMock()

    async def mock_get_db():
        yield mock_db

    with (
        patch("accounts_service.grpc_server.get_db", mock_get_db),
        patch("accounts_service.grpc_server.ensure_profile_and_settings", new_callable=AsyncMock) as mock_ensure,
    ):
        mock_ensure.return_value = data
        req = accounts_pb2.UpdateProfileRequest(
            user_context=common_pb2.UserContext(user_id="grpc_user"),
            profile=accounts_pb2.Profile(name="New Name", photo_url="http://img.png"),
        )
        res = await servicer.UpdateProfile(req, context)
        assert prof.display_name == "New Name"
        assert prof.photo_url == "http://img.png"
        assert res.profile.name == "New Name"


@pytest.mark.asyncio
async def test_grpc_health_servicer():
    """Verify gRPC HealthServicer Check and Watch methods."""
    servicer = HealthServicer()
    context = MagicMock()

    # Check
    resp = await servicer.Check(None, context)
    assert resp.status == health_pb2.HealthCheckResponse.SERVING

    # Watch
    context.cancelled.side_effect = [False, True]
    results = []
    async for item in servicer.Watch(None, context):
        results.append(item.status)
        break
    assert results == [health_pb2.HealthCheckResponse.SERVING]
