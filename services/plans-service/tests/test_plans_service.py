"""Unit and integration tests for plans-service."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from plans_service import models, schemas
from plans_service.config import Settings, get_settings
from plans_service.database import get_db
from plans_service.grpc_server import (
    HealthServicer,
    PlansServicer,
    _proto_calendar_plan,
    health_pb2,
    plans_pb2,
)
from plans_service.main import app
from plans_service.schemas.calendar_plan import (
    CalendarPlanCreate,
    CalendarPlanResponse,
    MesocycleResponse,
    MicrocycleResponse,
    PlanExerciseResponse,
    PlanSetResponse,
    PlanWorkoutResponse,
)
from plans_service.workout_calculation import WorkoutCalculator

# --- 1. Settings & Config Tests ---


def test_settings_initialization():
    """Verify Settings loads properly with default values."""
    s = Settings()
    assert s.GRPC_PORT == 50053
    assert s.SERVICE_PORT == 8005
    assert s.EXERCISES_SERVICE_URL == "http://exercises-service:8002"
    assert s.WORKOUTS_SERVICE_URL == "http://workouts-service:8004"
    assert s.USER_MAX_SERVICE_URL == "http://user-max-service:8003"
    assert s.RPE_SERVICE_URL == "http://rpe-service:8001"
    assert get_settings() is not None


# --- 2. Schemas & Models Tests ---


def test_calendar_plan_models():
    """Verify CalendarPlan and related models instantiation and repr."""
    plan = models.CalendarPlan(
        id=1,
        name="Hypertrophy 101",
        duration_weeks=8,
        user_id="user-123",
        root_plan_id=1,
    )
    assert repr(plan) == "<CalendarPlan(id=1, name='Hypertrophy 101')>"

    meso = models.Mesocycle(
        id=2,
        calendar_plan_id=1,
        name="Accumulation",
        duration_weeks=4,
        order_index=0,
    )
    assert "Accumulation" in repr(meso)

    micro = models.Microcycle(
        id=3,
        mesocycle_id=2,
        name="Week 1",
        order_index=0,
    )
    assert "Week 1" in repr(micro)

    pw = models.PlanWorkout(
        id=4,
        microcycle_id=3,
        day_label="Day 1",
    )
    assert "Day 1" in repr(pw)

    pe = models.PlanExercise(
        id=5,
        plan_workout_id=4,
        exercise_definition_id=15,
        exercise_name="Barbell Bench Press",
    )
    assert "Barbell Bench Press" in repr(pe)

    ps = models.PlanSet(
        id=6,
        plan_exercise_id=5,
        intensity=80,
        volume=5,
    )
    assert repr(ps) == "<PlanSet(id=6, plan_exercise_id=5, intensity=80)>"

    macro = models.PlanMacro(
        id=7,
        calendar_plan_id=1,
        name="Auto-Deload",
        rule_json='{"action": "Deload"}',
    )
    assert macro.name == "Auto-Deload"

    tpl = models.MesocycleTemplate(
        id=8,
        user_id="user-123",
        name="5/3/1 Template",
    )
    assert "5/3/1 Template" in repr(tpl)


def test_calendar_plan_create_schema():
    """Verify validation of CalendarPlanCreate schema."""
    data = {
        "name": "Strength Block",
        "duration_weeks": 6,
        "is_public": False,
        "mesocycles": [],
    }
    obj = CalendarPlanCreate.model_validate(data)
    assert obj.name == "Strength Block"
    assert obj.duration_weeks == 6


# --- 3. Workout Calculator Tests ---


@pytest.mark.asyncio
async def test_workout_calculator_true_1rm():
    """Verify 1RM calculation logic."""
    calc = WorkoutCalculator()
    with patch("plans_service.workout_calculation.get_intensity", new_callable=AsyncMock) as mock_get_intensity:
        mock_get_intensity.return_value = 85.0
        val = await calc.calculate_true_1rm(weight=100.0, reps=5, rpe=9.0)
        # 100 / 85.0 * 100 = 117.6
        assert val == 117.6

    # Test edge case: zero intensity returns None
    with patch("plans_service.workout_calculation.get_intensity", new_callable=AsyncMock) as mock_get_intensity:
        mock_get_intensity.return_value = 0.0
        val = await calc.calculate_true_1rm(weight=100.0, reps=5, rpe=9.0)
        assert val is None


# --- 4. gRPC Servicer Tests ---


def test_proto_calendar_plan_conversion():
    """Verify CalendarPlanResponse to protobuf CalendarPlan converter."""
    sample_plan = CalendarPlanResponse(
        id=1,
        name="Upper Lower Plan",
        duration_weeks=4,
        is_active=True,
        is_favorite=False,
        root_plan_id=1,
        is_original=True,
        mesocycles=[
            MesocycleResponse(
                id=10,
                name="Mesocycle 1",
                duration_weeks=4,
                order_index=0,
                microcycles=[
                    MicrocycleResponse(
                        id=20,
                        mesocycle_id=10,
                        name="Microcycle 1",
                        days_count=7,
                        order_index=0,
                        plan_workouts=[
                            PlanWorkoutResponse(
                                id=30,
                                microcycle_id=20,
                                day_label="Push",
                                order_index=0,
                                exercises=[
                                    PlanExerciseResponse(
                                        id=40,
                                        exercise_definition_id=15,
                                        exercise_name="Barbell Bench Press",
                                        notes="Paused reps",
                                        sets=[
                                            PlanSetResponse(
                                                id=50,
                                                plan_exercise_id=40,
                                                volume=5,
                                                working_weight=100.0,
                                                effort=9.0,
                                                intensity=85.0,
                                            )
                                        ],
                                    )
                                ],
                            )
                        ],
                    )
                ],
            )
        ],
    )

    proto = _proto_calendar_plan(sample_plan)
    assert proto is not None
    assert proto.id == 1
    assert proto.name == "Upper Lower Plan"
    assert len(proto.mesocycles) == 1
    assert proto.mesocycles[0].name == "Mesocycle 1"
    assert len(proto.mesocycles[0].microcycles) == 1
    assert proto.mesocycles[0].microcycles[0].name == "Microcycle 1"
    assert len(proto.mesocycles[0].microcycles[0].plan_workouts) == 1
    pw = proto.mesocycles[0].microcycles[0].plan_workouts[0]
    assert pw.day_label == "Push"
    assert pw.name == "Push"
    assert len(pw.exercises) == 1
    assert pw.exercises[0].exercise_definition_id == 15
    assert pw.exercises[0].notes == "Paused reps"
    assert len(pw.exercises[0].sets) == 1
    assert pw.exercises[0].sets[0].volume == 5
    assert pw.exercises[0].sets[0].working_weight == 100.0


@pytest.mark.asyncio
async def test_grpc_health_servicer():
    """Verify gRPC HealthServicer Check returns SERVING."""
    servicer = HealthServicer()
    resp = await servicer.Check(None, None)
    assert resp.status == health_pb2.HealthCheckResponse.SERVING


@pytest.mark.asyncio
async def test_grpc_validate_microcycles_empty():
    """Verify empty microcycle IDs validation in PlansServicer."""
    servicer = PlansServicer()
    req = plans_pb2.ValidateMicrocyclesRequest(microcycle_ids=[])
    context = AsyncMock()
    resp = await servicer.ValidateMicrocycles(req, context)
    assert list(resp.valid_ids) == []


# --- 5. HTTP Endpoints Tests with TestClient ---


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client):
    """Verify GET /health returns status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_endpoint(client):
    """Verify GET / returns welcome message."""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_calendar_plan_not_found_returns_404(client):
    """Verify GET /plans/calendar-plans/{id} returns 404 not 500 when plan does not exist."""
    headers = {"X-User-ID": "test-user-404"}
    with patch("plans_service.services.calendar_plan_service.CalendarPlanService.get_plan", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None
        response = client.get("/plans/calendar-plans/99999", headers=headers)
        assert response.status_code == 404
        assert response.json()["detail"] == "Plan not found"


def test_internal_purge_unauthorized(client):
    """Verify POST /internal/users/{id}/purge requires valid secret."""
    response = client.post("/internal/users/usr1/purge", headers={"X-Internal-Secret": "wrong"})
    assert response.status_code == 403
