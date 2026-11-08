"""Comprehensive test suite for agent-service."""

from __future__ import annotations

import io
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from agent_service.config import Settings, get_settings, settings
from agent_service.database import Base, SessionLocal, engine, get_db
from agent_service.dependencies import get_current_user_id
from agent_service.main import app
from agent_service.models import Avatar, GeneratedPlan
from agent_service.schemas import (
    mass_edit as mass_edit_schemas,
    task_responses as task_schemas,
    training_plans as plan_schemas,
    user_data as user_schemas,
)
from agent_service.services.plans_service import save_plan_to_plans_service
from agent_service.services.rpe_rpc import notify_rpe_plan_created
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Setup in-memory DB tables for tests
Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def clean_db():
    """Clean test DB before each test."""
    session = SessionLocal()
    try:
        session.query(GeneratedPlan).delete()
        session.query(Avatar).delete()
        session.commit()
    finally:
        session.close()
    yield


@pytest.fixture
def client():
    """Create a test client with mocked user dependency."""
    app.dependency_overrides[get_current_user_id] = lambda: "test-user-123"
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ==============================================================================
# 1. Settings & Config Tests
# ==============================================================================


def test_settings_initialization():
    s = Settings()
    assert s.LLM_PROVIDER in ["gemini", "fireworks"]
    assert s.llm_provider in ["gemini", "fireworks"]
    assert bool(s.llm_model)
    assert s.user_max_service_url == "http://user-max-service:8003"
    assert s.exercises_service_url == "http://exercises-service:8002"
    assert s.plans_service_url == "http://plans-service:8005"
    assert s.workouts_service_url == "http://workouts-service:8004"
    assert s.crm_service_url == "http://crm-service:8008"
    assert s.rpe_service_url == "http://rpe-service:8001"
    assert s.celery_task_timeout_seconds >= 30
    assert s.genai_max_attempts >= 1
    assert get_settings() is not None


# ==============================================================================
# 2. Database Models & Storage Tests
# ==============================================================================


def test_database_models_crud():
    session = SessionLocal()
    try:
        # Create GeneratedPlan
        plan_data = {"test": "data", "intensity": 80}
        plan = GeneratedPlan(user_id="user-456", plan_data=plan_data)
        session.add(plan)
        session.commit()
        session.refresh(plan)

        assert plan.id is not None
        assert plan.user_id == "user-456"
        assert plan.plan_data == plan_data
        assert isinstance(plan.created_at, datetime)

        # Create Avatar
        raw_img = b"PNG_TEST_IMAGE_DATA_12345"
        avatar = Avatar(user_id="user-456", image=raw_img, content_type="image/png")
        session.add(avatar)
        session.commit()
        session.refresh(avatar)

        assert avatar.user_id == "user-456"
        assert avatar.image == raw_img
        assert avatar.content_type == "image/png"
    finally:
        session.close()


def test_get_db_generator():
    db_gen = get_db()
    db_session = next(db_gen)
    assert isinstance(db_session, Session)
    with pytest.raises(StopIteration):
        next(db_gen)


# ==============================================================================
# 3. Schemas Validation Tests
# ==============================================================================


def test_training_plans_schemas():
    plan_set = plan_schemas.PlanSet(
        id=1,
        plan_exercise_id=10,
        order_index=1,
        intensity=80,
        effort=8,
        volume=5,
    )
    assert plan_set.intensity == 80
    assert plan_set.model_dump()["volume"] == 5

    user_data = user_schemas.UserDataInput(
        goals=["hypertrophy", "strength"],
        available_equipment=["barbell", "dumbbells"],
        workouts_per_microcycle=4,
    )
    assert len(user_data.goals) == 2
    assert user_data.workouts_per_microcycle == 4


def test_mass_edit_schemas():
    req = mass_edit_schemas.AgentPlanMassEditRequest(
        plan_id=10,
        mode="apply",
        prompt="Increase intensity on bench press",
    )
    assert req.plan_id == 10
    assert req.mode == "apply"

    shift_req = mass_edit_schemas.AgentAppliedPlanScheduleShiftRequest(
        applied_plan_id=5,
        from_date="2026-10-12",
        days=2,
    )
    assert shift_req.days == 2


# ==============================================================================
# 4. Internal Purge Router Tests
# ==============================================================================


def test_internal_purge_unauthorized(client):
    with patch.object(settings, "INTERNAL_GATEWAY_SECRET", "super-secret"):
        # Missing secret
        resp = client.post("/internal/users/user-123/purge")
        assert resp.status_code == 403

        # Invalid secret
        resp = client.post(
            "/internal/users/user-123/purge",
            headers={"X-Internal-Secret": "wrong-secret"},
        )
        assert resp.status_code == 403


def test_internal_purge_success(client):
    # Seed data
    session = SessionLocal()
    try:
        session.add(GeneratedPlan(user_id="user-to-purge", plan_data={"a": 1}))
        session.add(Avatar(user_id="user-to-purge", image=b"image_content_bytes_123"))
        session.add(GeneratedPlan(user_id="keep-user", plan_data={"b": 2}))
        session.commit()
    finally:
        session.close()

    with patch.object(settings, "INTERNAL_GATEWAY_SECRET", "super-secret"):
        resp = client.post(
            "/internal/users/user-to-purge/purge",
            headers={"X-Internal-Secret": "super-secret"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["deleted_plans"] == 1
        assert data["deleted_avatars"] == 1

    # Verify DB state
    session = SessionLocal()
    try:
        assert session.query(GeneratedPlan).filter_by(user_id="user-to-purge").count() == 0
        assert session.query(Avatar).filter_by(user_id="user-to-purge").count() == 0
        assert session.query(GeneratedPlan).filter_by(user_id="keep-user").count() == 1
    finally:
        session.close()


# ==============================================================================
# 5. Health & Root Endpoints Tests
# ==============================================================================


def test_root_endpoint(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json() == {"message": "Agent service is running"}


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "service": "agent-service"}


# ==============================================================================
# 6. Avatars Router Tests
# ==============================================================================


def test_avatar_apply_and_get(client):
    fake_png = b"PNG_MOCK_IMAGE_DATA_LONGER_THAN_16_BYTES"

    # Test empty body
    resp = client.post(
        "/avatars/apply",
        content=b"",
        headers={"X-User-Id": "test-user-123"},
    )
    assert resp.status_code == 400

    # Test too short body
    resp = client.post(
        "/avatars/apply",
        content=b"short",
        headers={"X-User-Id": "test-user-123"},
    )
    assert resp.status_code == 400

    # Test successful apply
    resp = client.post(
        "/avatars/apply",
        content=fake_png,
        headers={"X-User-Id": "test-user-123", "Content-Type": "image/png"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"uid": "test-user-123", "ok": True}

    # Test retrieve avatar
    resp = client.get("/avatars/test-user-123.png")
    assert resp.status_code == 200
    assert resp.content == fake_png
    assert resp.headers["content-type"] == "image/png"

    # Test avatar not found
    resp = client.get("/avatars/unknown-user.png")
    assert resp.status_code == 404


def test_avatar_generate_missing_token(client):
    with patch.object(settings, "HF_TOKEN", None), patch.dict("os.environ", {}, clear=True):
        resp = client.post(
            "/avatars/generate",
            json={"prompt": "fit warrior"},
            headers={"X-User-Id": "test-user-123"},
        )
        assert resp.status_code == 500
        assert "HF_TOKEN is not configured" in resp.json()["detail"]


@patch("httpx.AsyncClient.post")
def test_avatar_generate_success(mock_post, client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"GEN_PNG_DATA_1234567890"
    mock_resp.raise_for_status = MagicMock()
    mock_post.return_value = mock_resp

    with patch.object(settings, "HF_TOKEN", "hf_test_token_123"):
        resp = client.post(
            "/avatars/generate",
            json={"prompt": "athletic runner"},
            headers={"X-User-Id": "test-user-123"},
        )
        assert resp.status_code == 200
        assert resp.content == b"GEN_PNG_DATA_1234567890"
        assert resp.headers["content-type"] == "image/png"


# ==============================================================================
# 7. Training Plans & Mass Edit Tasks Submission Endpoints
# ==============================================================================


@patch("agent_service.routers.training_plans.enqueue_task")
def test_training_plans_endpoints(mock_enqueue, client):
    mock_enqueue.return_value = {"task_id": "test-task-uuid-1", "status": "PENDING"}

    payload = {
        "goals": ["strength"],
        "available_equipment": ["barbell"],
        "workouts_per_microcycle": 3,
    }

    # Generate plan
    resp = client.post("/training-plans/generate-plan/", json=payload, headers={"X-User-Id": "test-user-123"})
    assert resp.status_code == 200
    assert resp.json()["task_id"] == "test-task-uuid-1"

    # Generate plan with rationale
    resp = client.post("/training-plans/generate-plan-with-rationale/", json=payload, headers={"X-User-Id": "test-user-123"})
    assert resp.status_code == 200
    assert resp.json()["task_id"] == "test-task-uuid-1"

    # Generate plan with summary
    resp = client.post("/training-plans/generate-plan-with-summary/", json=payload, headers={"X-User-Id": "test-user-123"})
    assert resp.status_code == 200
    assert resp.json()["task_id"] == "test-task-uuid-1"


@patch("agent_service.routers.plan_mass_edit.enqueue_task")
def test_plan_mass_edit_endpoints(mock_enqueue, client):
    mock_enqueue.return_value = {"task_id": "mass-task-uuid-2", "status": "PENDING"}

    resp = client.post(
        "/agent/plan-mass-edit",
        json={"plan_id": 1, "mode": "apply", "prompt": "make it harder"},
        headers={"X-User-Id": "test-user-123"},
    )
    assert resp.status_code == 200
    assert resp.json()["task_id"] == "mass-task-uuid-2"

    resp = client.post(
        "/agent/applied-plan-mass-edit",
        json={"applied_plan_id": 1, "mode": "apply", "prompt": "swap squat for leg press"},
        headers={"X-User-Id": "test-user-123"},
    )
    assert resp.status_code == 200
    assert resp.json()["task_id"] == "mass-task-uuid-2"

    resp = client.post(
        "/agent/applied-plan-shift-schedule",
        json={"applied_plan_id": 1, "from_date": "2026-10-12", "days": 1},
        headers={"X-User-Id": "test-user-123"},
    )
    assert resp.status_code == 200
    assert resp.json()["task_id"] == "mass-task-uuid-2"


@patch("agent_service.routers.training_plans.build_task_status_response")
def test_task_status_endpoint(mock_status, client):
    mock_status.return_value = task_schemas.TaskStatusResponse(
        task_id="task-123",
        status="SUCCESS",
        result={"plan_id": 1},
    )

    resp = client.get("/training-plans/tasks/task-123")
    assert resp.status_code == 200
    assert resp.json()["status"] == "SUCCESS"
    assert resp.json()["result"] == {"plan_id": 1}


# ==============================================================================
# 8. Downstream Services RPC Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_notify_rpe_plan_created():
    mock_plan = MagicMock()
    mock_plan.model_dump.return_value = {"id": 123}

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        success = await notify_rpe_plan_created(mock_plan, user_id="user-1")
        assert success is True

    # Error case
    with patch("httpx.AsyncClient.post", side_effect=Exception("Connection refused")):
        success = await notify_rpe_plan_created(mock_plan, user_id="user-1")
        assert success is False


@pytest.mark.asyncio
async def test_save_plan_to_plans_service():
    plan = plan_schemas.TrainingPlan(
        calendar_plan=plan_schemas.CalendarPlan(id=1, name="Plan 1", duration_weeks=4),
        mesocycles=[],
        microcycles=[],
        workouts=[],
        exercises=[],
        sets=[],
    )

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": 99, "name": "Plan 1"}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = await save_plan_to_plans_service(plan, user_id="user-1")
        assert result == {"id": 99, "name": "Plan 1"}

    # Error case returns None
    with patch("httpx.AsyncClient.post", side_effect=Exception("Network error")):
        result = await save_plan_to_plans_service(plan, user_id="user-1")
        assert result is None
