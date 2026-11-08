"""Unit and integration tests for crm-service."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from crm_service import schemas
from crm_service.config import Settings, get_settings, settings
from crm_service.dependencies import get_current_user_id, get_db
from crm_service.main import app
from crm_service.schemas.coach_planning import EffortType, ExerciseSet
from crm_service.schemas.relationships import CoachAthleteStatus
from crm_service.services import analytics_service, relationships_service
from fastapi import HTTPException
from fastapi.testclient import TestClient

# --- 1. Settings & Config Tests ---


def test_settings_initialization():
    """Verify Settings loads properly with default values and property access."""
    s = Settings()
    assert s.WORKOUTS_SERVICE_URL == "http://workouts-service:8004"
    assert s.workouts_service_url == "http://workouts-service:8004"
    assert s.PLANS_SERVICE_URL == "http://plans-service:8005"
    assert s.plans_service_url == "http://plans-service:8005"
    assert s.EXERCISES_SERVICE_URL == "http://exercises-service:8002"
    assert s.exercises_service_url == "http://exercises-service:8002"
    assert s.AGENT_SERVICE_URL == "http://agent-service:8006"
    assert s.agent_service_url == "http://agent-service:8006"
    assert s.ACCOUNTS_SERVICE_URL == "http://accounts-service:8007"
    assert s.accounts_service_url == "http://accounts-service:8007"
    assert s.CRM_DATABASE_URL is not None
    assert get_settings() is not None


# --- 2. Schemas & Enums Tests ---


def test_enums_and_schemas_validations():
    """Verify enum values and validation logic in schemas."""
    assert CoachAthleteStatus.pending == "pending"
    assert CoachAthleteStatus.active == "active"
    assert CoachAthleteStatus.paused == "paused"
    assert CoachAthleteStatus.ended == "ended"

    assert EffortType.RPE == "RPE"
    assert EffortType.RIR == "RIR"

    # Review rating validation
    with pytest.raises(Exception):
        schemas.CoachReviewCreate(rating=0)
    with pytest.raises(Exception):
        schemas.CoachReviewCreate(rating=6)
    valid_review = schemas.CoachReviewCreate(rating=5, comment="Great coach!")
    assert valid_review.rating == 5

    # ExerciseSet extra fields allowed
    set_obj = ExerciseSet(weight=100.0, volume=5, extra_field="custom_val")
    assert set_obj.weight == 100.0
    assert getattr(set_obj, "extra_field", None) == "custom_val"

    # Tag validation
    with pytest.raises(Exception):
        schemas.CoachAthleteTagBase(name="")
    tag = schemas.CoachAthleteTagCreate(name="Powerlifting", is_global=True)
    assert tag.name == "Powerlifting"
    assert tag.is_global is True


# --- 3. Analytics Service Helper Logic Tests ---


def test_classify_athlete_segment():
    """Test athlete classification logic."""
    # New athlete: < 2 sessions and no plan
    assert (
        analytics_service._classify_athlete_segment(
            sessions_per_week=0.5,
            plan_adherence=None,
            days_since_last_workout=None,
            inactive_after_days=14,
            has_plan=False,
            sessions_count=1,
        )
        == "new"
    )

    # Top performer: >= 3.0 sessions/week, adherence >= 0.8, recent workout
    assert (
        analytics_service._classify_athlete_segment(
            sessions_per_week=4.0,
            plan_adherence=0.9,
            days_since_last_workout=2,
            inactive_after_days=14,
            has_plan=True,
            sessions_count=12,
        )
        == "top_performer"
    )

    # At risk: low sessions per week
    assert (
        analytics_service._classify_athlete_segment(
            sessions_per_week=0.8,
            plan_adherence=0.9,
            days_since_last_workout=2,
            inactive_after_days=14,
            has_plan=True,
            sessions_count=5,
        )
        == "at_risk"
    )

    # At risk: low plan adherence
    assert (
        analytics_service._classify_athlete_segment(
            sessions_per_week=2.5,
            plan_adherence=0.2,
            days_since_last_workout=2,
            inactive_after_days=14,
            has_plan=True,
            sessions_count=10,
        )
        == "at_risk"
    )

    # At risk: inactive for too long
    assert (
        analytics_service._classify_athlete_segment(
            sessions_per_week=2.0,
            plan_adherence=0.7,
            days_since_last_workout=20,
            inactive_after_days=14,
            has_plan=True,
            sessions_count=10,
        )
        == "at_risk"
    )

    # On track: normal active athlete
    assert (
        analytics_service._classify_athlete_segment(
            sessions_per_week=2.5,
            plan_adherence=0.75,
            days_since_last_workout=3,
            inactive_after_days=14,
            has_plan=True,
            sessions_count=10,
        )
        == "on_track"
    )


def test_aggregate_plan_metrics():
    """Test aggregation of metrics from plan items."""
    # Empty plan items
    avg_int, avg_eff, rpe_dist, vol = analytics_service._aggregate_plan_metrics([])
    assert avg_int is None
    assert avg_eff is None
    assert rpe_dist is None
    assert vol == 0.0

    # With items
    items = [
        {
            "metrics": {
                "intensity_avg": 80.0,
                "effort_avg": 8.0,
                "volume_sum": 1000.0,
                "sets_count": 5,
            }
        },
        {
            "metrics": {
                "intensity_avg": 85.0,
                "effort_avg": 9.0,
                "volume_sum": 1200.0,
                "sets_count": 5,
            }
        },
    ]
    avg_int, avg_eff, rpe_dist, vol = analytics_service._aggregate_plan_metrics(items)
    assert avg_int == 82.5
    assert avg_eff == 8.5
    assert vol == 2200.0
    assert isinstance(rpe_dist, dict)
    assert rpe_dist["8"] == 0.5
    assert rpe_dist["9"] == 0.5


def test_aggregate_muscle_metrics_from_actual():
    """Test muscle metrics breakdown aggregation."""
    items = [
        {
            "actual_metrics": {
                "muscle_group:Chest": 500.0,
                "muscle:Pectoralis Major": 500.0,
            }
        },
        {
            "actual_metrics": {
                "muscle_group:Chest": 300.0,
                "muscle_group:Back": 400.0,
            }
        },
    ]
    groups, muscles = analytics_service._aggregate_muscle_metrics_from_actual(items)
    assert groups is not None
    assert groups["Chest"] == 800.0
    assert groups["Back"] == 400.0
    assert muscles is not None
    assert muscles["Pectoralis Major"] == 500.0


# --- 4. Relationships Service Unit Tests ---


@pytest.mark.asyncio
async def test_create_link_same_user_raises():
    """Coach and athlete cannot be the same user."""
    mock_db = AsyncMock()
    payload = schemas.CoachAthleteLinkCreate(coach_id="user1", athlete_id="user1")
    with pytest.raises(HTTPException) as exc_info:
        await relationships_service.create_link(mock_db, coach_id="user1", payload=payload)
    assert exc_info.value.status_code == 400
    assert "Coach and athlete must be different users" in exc_info.value.detail


@pytest.mark.asyncio
async def test_create_link_missing_both_ids_raises():
    """Must provide either athlete_id or coach_id."""
    mock_db = AsyncMock()
    payload = schemas.CoachAthleteLinkCreate()
    with pytest.raises(HTTPException) as exc_info:
        await relationships_service.create_link(mock_db, coach_id="user1", payload=payload)
    assert exc_info.value.status_code == 422


# --- 5. Integration Tests with TestClient ---


@pytest.fixture
def test_client():
    """Create a FastAPI test client with mocked dependencies."""
    mock_session = AsyncMock()

    async def override_get_db():
        yield mock_session

    def override_get_current_user_id():
        return "test-user-123"

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = override_get_current_user_id
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_health_endpoint(test_client):
    """GET /health should return 200 ok."""
    resp = test_client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_internal_purge_unauthorized(test_client):
    """Internal purge without valid secret should return 403."""
    resp = test_client.post("/internal/users/user-to-purge/purge")
    assert resp.status_code == 403


def test_internal_purge_authorized(test_client):
    """Internal purge with matching secret should succeed."""
    secret = settings.INTERNAL_GATEWAY_SECRET or "test-secret"
    with patch.object(settings, "INTERNAL_GATEWAY_SECRET", secret):
        resp = test_client.post(
            "/internal/users/user-to-purge/purge",
            headers={"X-Internal-Secret": secret},
        )
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


def test_coach_planning_mass_edit_empty(test_client):
    """POST /crm/coach/athletes/{athlete_id}/workouts/mass-edit should return 200 with results dict."""
    with patch(
        "crm_service.routers.coach_planning.mass_edit_workouts_for_athlete",
        new=AsyncMock(return_value={"workouts": [], "exercise_instances": []}),
    ):
        resp = test_client.post(
            "/crm/coach/athletes/athlete-1/workouts/mass-edit",
            json={"workouts": [], "exercise_instances": []},
        )
        assert resp.status_code == 200
        assert resp.json() == {"workouts": [], "exercise_instances": []}


def test_get_coach_reviews_empty(test_client):
    """GET /crm/reviews/coaches/{coach_id}/reviews returns paginated reviews list."""
    with patch(
        "crm_service.routers.reviews.get_reviews_for_coach",
        new=AsyncMock(
            return_value=schemas.CoachReviewListResponse(
                reviews=[],
                total=0,
                limit=100,
                offset=0,
            )
        ),
    ):
        resp = test_client.get("/crm/reviews/coaches/coach-1/reviews")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["reviews"] == []


def test_get_my_athletes_analytics(test_client):
    """GET /crm/analytics/coaches/my/athletes returns summary analytics."""
    with patch(
        "crm_service.routers.analytics.get_coach_athletes_analytics",
        new=AsyncMock(
            return_value=schemas.CoachAthletesAnalyticsResponse(
                coach_id="test-user-123",
                generated_at=datetime.now(UTC),
                weeks=12,
                total_athletes=0,
                active_links=0,
                athletes=[],
            )
        ),
    ):
        resp = test_client.get("/crm/analytics/coaches/my/athletes")
        assert resp.status_code == 200
        data = resp.json()
        assert data["coach_id"] == "test-user-123"
        assert data["total_athletes"] == 0
