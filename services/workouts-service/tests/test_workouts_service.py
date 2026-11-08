"""Unit and integration tests for workouts-service."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from workouts_service import models, schemas
from workouts_service.config import Settings, get_settings, settings
from workouts_service.database import get_db
from workouts_service.exceptions import WorkoutNotFoundException
from workouts_service.grpc_server import (
    HealthServicer,
    WorkoutServicer,
    _proto_exercise_instance,
    _proto_workout,
    _proto_workout_session,
    common_pb2,
    health_pb2,
    workouts_pb2,
)
from workouts_service.main import app
from workouts_service.services.user_max_client import UserMaxClient
from workouts_service.workout_calculation import WorkoutCalculator

# --- 1. Settings & Config Tests ---


def test_settings_initialization():
    """Verify Settings loads properly with default values."""
    s = Settings()
    assert s.GRPC_PORT == 50054
    assert s.SERVICE_PORT == 8004
    assert s.WORKOUTS_REDIS_HOST is not None
    assert get_settings() is not None


# --- 2. Schemas & Models Tests ---


def test_workout_models():
    """Verify Workout and related models instantiation and repr."""
    workout = models.Workout(
        id=1,
        user_id="user-123",
        name="Leg Day",
        applied_plan_id=10,
        plan_order_index=1,
        status="pending",
    )
    assert repr(workout) == "<Workout(id=1, name='Leg Day', applied_plan_id=10, order=1)>"

    session = models.WorkoutSession(
        id=5,
        user_id="user-123",
        workout_id=1,
        status="active",
    )
    assert repr(session) == "<WorkoutSession(id=5, workout_id=1, status=active)>"

    we = models.WorkoutExercise(
        id=100,
        user_id="user-123",
        workout_id=1,
        exercise_id=35,
        order=1,
        notes="Squats",
    )
    assert we.exercise_id == 35

    ws = models.WorkoutSet(
        id=200,
        exercise_id=100,
        order_index=0,
        intensity=80.0,
        effort=8.0,
        volume=5,
        working_weight=100.0,
    )
    assert ws.volume == 5


def test_schema_validations():
    """Verify Pydantic schemas in workouts_service."""
    create = schemas.workout.WorkoutCreate(
        name="Chest Day",
        notes="Bench focus",
        workout_type="manual",
    )
    assert create.name == "Chest Day"
    assert create.workout_type == schemas.workout.WorkoutTypeEnum.manual

    # Extra forbidden attributes in WorkoutCreate
    with pytest.raises(Exception):
        schemas.workout.WorkoutCreate(
            name="Invalid",
            unknown_extra_field=123,
        )


# --- 3. Calculations & Logic Tests ---


@pytest.mark.asyncio
async def test_workout_calculator_true_1rm():
    """Verify true 1RM calculation with precalculated true_1rm."""
    # Precalculated true_1rm priority
    data = {"true_1rm": 140.0, "max_weight": 100.0, "rep_max": 5}
    val = await WorkoutCalculator.get_true_1rm_from_user_max(data)
    assert val == 140.0

    # Calculate from Epley when true_1rm is absent
    data2 = {"max_weight": 100.0, "rep_max": 5}
    val2 = await WorkoutCalculator.get_true_1rm_from_user_max(data2)
    assert val2 is not None
    assert round(val2, 2) == 116.65

    # 1 rep or <=0 reps returns max_weight
    data3 = {"max_weight": 120.0, "rep_max": 0}
    val3 = await WorkoutCalculator.get_true_1rm_from_user_max(data3)
    assert val3 == 120.0

    # Empty data returns None
    assert await WorkoutCalculator.get_true_1rm_from_user_max(None) is None
    assert await WorkoutCalculator.get_true_1rm_from_user_max({}) is None


def test_workout_calculator_normalization():
    """Verify normalization rules for percentage and absolute units."""
    calc = WorkoutCalculator()
    effective = {35: 100.0, 15: 80.0}

    # Percentage normalization (+10%)
    calc._apply_normalization(effective, 10.0, "percentage")
    assert round(effective[35], 1) == 110.0
    assert round(effective[15], 1) == 88.0

    # Absolute normalization (+5 kg)
    calc._apply_normalization(effective, 5.0, "absolute")
    assert round(effective[35], 1) == 115.0
    assert round(effective[15], 1) == 93.0

    # None values are no-op
    calc._apply_normalization(effective, None, "percentage")
    assert round(effective[35], 1) == 115.0


def test_user_max_client_normalization():
    """Verify user max client entry normalization."""
    client = UserMaxClient()
    entry = {
        "exercise_id": "35",
        "max_weight": "120.5",
        "rep_max": "3",
        "date": "2026-05-10",
    }
    norm = client._normalize_entry(entry)
    assert norm == {
        "exercise_id": 35,
        "max_weight": 120.5,
        "rep_max": 3,
        "date": "2026-05-10",
    }

    # Invalid entry returns None
    assert client._normalize_entry({"exercise_id": "invalid"}) is None


# --- 4. HTTP API & Exception Handler Tests ---


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client):
    """Verify /health returns 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_not_found_exception_handler(client):
    """Verify custom NotFoundException handler."""
    exc = WorkoutNotFoundException(99999)
    assert exc.status_code == 404
    assert "99999" in exc.detail


def test_internal_purge_endpoint(client):
    """Verify /internal/users/{user_id}/purge authentication and execution."""
    with patch.object(settings, "INTERNAL_GATEWAY_SECRET", "super-secret"):
        # Without or with wrong secret -> 403 Forbidden
        resp = client.post(
            "/internal/users/test-user/purge",
            headers={"X-Internal-Secret": "wrong-secret"},
        )
        assert resp.status_code == 403

        # With valid secret -> 200 OK
        with patch("workouts_service.routers.internal_purge.get_redis", return_value=None):
            mock_session = AsyncMock()
            app.dependency_overrides[get_db] = lambda: mock_session
            try:
                resp = client.post(
                    "/internal/users/test-user/purge",
                    headers={"X-Internal-Secret": "super-secret"},
                )
                assert resp.status_code == 200
                assert resp.json() == {"status": "ok"}
            finally:
                app.dependency_overrides.pop(get_db, None)


# --- 5. gRPC Servicer Tests ---


def test_proto_conversions():
    """Verify Workout, WorkoutExercise, and Session proto serialization."""
    # WorkoutExercise conversion
    we = models.WorkoutExercise(
        id=1,
        user_id="user-1",
        workout_id=10,
        exercise_id=15,
        order=0,
        notes="Pause at chest",
        sets=[
            models.WorkoutSet(
                id=101,
                order_index=0,
                volume=8,
                working_weight=80.0,
                effort=8.0,
                intensity=75.0,
            )
        ],
    )
    proto_inst = _proto_exercise_instance(we)
    assert proto_inst is not None
    assert proto_inst.id == 1
    assert proto_inst.exercise_list_id == 15
    assert len(proto_inst.sets) == 1
    assert proto_inst.sets[0].reps == 8
    assert proto_inst.sets[0].working_weight == 80.0

    # Workout conversion
    workout = models.Workout(
        id=10,
        name="Upper Body",
        status="pending",
        workout_type="manual",
        applied_plan_id=5,
        plan_order_index=1,
        exercises=[we],
    )
    proto_w = _proto_workout(workout)
    assert proto_w is not None
    assert proto_w.id == 10
    assert proto_w.name == "Upper Body"
    assert len(proto_w.exercise_instances) == 1

    # Session conversion
    now = datetime(2026, 10, 8, 12, 0, 0)
    session = models.WorkoutSession(
        id=20,
        user_id="user-1",
        workout_id=10,
        status="active",
        started_at=now,
    )
    session.workout = workout
    proto_s = _proto_workout_session(session)
    assert proto_s is not None
    assert proto_s.id == 20
    assert proto_s.status == "active"
    assert proto_s.started_at.endswith("Z")


@pytest.mark.asyncio
async def test_grpc_servicer_get_workout_bug_fix():
    """Verify GetWorkout executes selectinload(WorkoutExercise.sets) without NameError."""
    servicer = WorkoutServicer()
    mock_context = MagicMock()
    request = workouts_pb2.GetWorkoutRequest(
        workout_id=42,
        user_context=common_pb2.UserContext(user_id="user-test"),
    )

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_workout = models.Workout(
        id=42,
        user_id="user-test",
        name="Deadlift Session",
        status="pending",
        workout_type="manual",
        exercises=[],
    )
    mock_result.scalar_one_or_none.return_value = mock_workout
    mock_db.execute.return_value = mock_result

    async def mock_get_db():
        yield mock_db

    with patch("workouts_service.grpc_server.get_db", side_effect=mock_get_db):
        resp = await servicer.GetWorkout(request, mock_context)
        assert resp is not None
        assert resp.workout.id == 42
        assert resp.workout.name == "Deadlift Session"


@pytest.mark.asyncio
async def test_grpc_servicer_update_workout_bug_fix():
    """Verify UpdateWorkout executes selectinload(WorkoutExercise.sets) without NameError."""
    servicer = WorkoutServicer()
    mock_context = MagicMock()
    request = workouts_pb2.UpdateWorkoutRequest(
        workout_id=42,
        workout=workouts_pb2.Workout(name="Updated Deadlift", status="completed"),
        user_context=common_pb2.UserContext(user_id="user-test"),
    )

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_workout = models.Workout(
        id=42,
        user_id="user-test",
        name="Deadlift Session",
        status="pending",
        workout_type="manual",
        exercises=[],
    )
    mock_result.scalar_one_or_none.return_value = mock_workout
    mock_db.execute.return_value = mock_result

    async def mock_get_db():
        yield mock_db

    with patch("workouts_service.grpc_server.get_db", side_effect=mock_get_db):
        resp = await servicer.UpdateWorkout(request, mock_context)
        assert resp is not None
        assert resp.workout.name == "Updated Deadlift"
        assert resp.workout.status == "completed"


@pytest.mark.asyncio
async def test_grpc_health_servicer():
    """Verify HealthServicer Check and Watch methods."""
    servicer = HealthServicer()
    context = MagicMock()

    # Check
    check_resp = await servicer.Check(None, context)
    assert check_resp.status == health_pb2.HealthCheckResponse.SERVING

    # Watch
    context.cancelled.side_effect = [False, True]
    results = []
    async for item in servicer.Watch(None, context):
        results.append(item.status)
        break
    assert results == [health_pb2.HealthCheckResponse.SERVING]
