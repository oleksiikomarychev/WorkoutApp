import os
import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from workouts_service.database import Base
from workouts_service.models import Workout, WorkoutExercise, WorkoutSet
from workouts_service.routers.internal_purge import cleanup_failed_application
from workouts_service.schemas.applied_mass_edit import (
    AppliedPlanExerciseActions,
    AppliedPlanExerciseFilter,
    AppliedPlanMassEditCommand,
    AppliedPlanScheduleShiftCommand,
)
from workouts_service.services.exercise_instance_service import ExerciseInstanceService
from workouts_service.services.workout_service import WorkoutService


@pytest.fixture
async def db_factory():
    url = os.getenv("CONTRACT_TEST_POSTGRES_URL")
    admin = None
    schema = "contract_" + uuid.uuid4().hex
    if url:
        admin = create_async_engine(url)
        async with admin.begin() as conn:
            await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
    else:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()
    if admin is not None:
        async with admin.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin.dispose()


async def seed(factory, *, status="pending", completed_at=None):
    if completed_at is not None:
        completed_at = completed_at.astimezone(UTC).replace(tzinfo=None)
    async with factory() as db:
        workout = Workout(
            user_id="user-1",
            name="A",
            applied_plan_id=7,
            plan_order_index=0,
            status=status,
            completed_at=completed_at,
            workout_type="generated",
        )
        db.add(workout)
        await db.flush()
        exercise = WorkoutExercise(user_id="user-1", workout_id=workout.id, exercise_id=8)
        db.add(exercise)
        await db.flush()
        db.add_all(
            [
                WorkoutSet(exercise_id=exercise.id, volume=5, working_weight=10.0),
                WorkoutSet(exercise_id=exercise.id, volume=5, working_weight=20.0),
            ]
        )
        await db.commit()


def command():
    return AppliedPlanMassEditCommand(
        mode="apply",
        filter=AppliedPlanExerciseFilter(plan_order_indices=[0], only_future=False),
        actions=AppliedPlanExerciseActions(set_weight=50.0),
    )


@pytest.mark.asyncio
async def test_failed_second_set_rolls_back_first(db_factory):
    await seed(db_factory)
    original = ExerciseInstanceService.update_set
    calls = 0

    async def fail_second(self, instance_id, set_id, payload, *, commit=True):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("second set failed")
        return await original(self, instance_id, set_id, payload, commit=commit)

    async with db_factory() as db:
        with patch.object(ExerciseInstanceService, "update_set", fail_second):
            with pytest.raises(RuntimeError, match="second set failed"):
                await WorkoutService(db, None, user_id="user-1").apply_applied_plan_mass_edit(7, command())
        await db.rollback()
    async with db_factory() as db:
        weights = list((await db.execute(select(WorkoutSet.working_weight).order_by(WorkoutSet.id))).scalars())
    assert weights == [10.0, 20.0]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "completed_at"),
    [("completed", None), ("pending", datetime(2026, 11, 10, tzinfo=UTC))],
)
async def test_completed_workout_is_excluded(db_factory, status, completed_at):
    await seed(db_factory, status=status, completed_at=completed_at)
    async with db_factory() as db:
        result = await WorkoutService(db, None, user_id="user-1").apply_applied_plan_mass_edit(7, command())
        assert result.workouts_matched == 0
    async with db_factory() as db:
        weights = list((await db.execute(select(WorkoutSet.working_weight).order_by(WorkoutSet.id))).scalars())
    assert weights == [10.0, 20.0]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "completed_at"),
    [("completed", None), ("pending", datetime(2026, 11, 10, tzinfo=UTC))],
)
async def test_schedule_shift_keeps_completed_workout(db_factory, status, completed_at):
    await seed(db_factory, status=status, completed_at=completed_at)
    original_date = datetime(2026, 11, 12)
    async with db_factory() as db:
        workout = (await db.execute(select(Workout))).scalar_one()
        workout.scheduled_for = original_date
        await db.commit()
    cmd = AppliedPlanScheduleShiftCommand(
        from_date=datetime(2026, 11, 1, tzinfo=UTC), days=3, only_future=False, mode="apply"
    )
    async with db_factory() as db:
        result = await WorkoutService(db, None, user_id="user-1").shift_applied_plan_schedule_from_date(7, cmd)
        assert result["workouts_shifted"] == 0
    async with db_factory() as db:
        workout = (await db.execute(select(Workout))).scalar_one()
        assert workout.scheduled_for == original_date


@pytest.mark.asyncio
async def test_generated_workout_is_listed_before_plan_commit(db_factory):
    await seed(db_factory)
    async with db_factory() as db:
        workouts = await WorkoutService(db, None, user_id="user-1").list_workouts(applied_plan_id=7)
    assert len(workouts) == 1
    assert workouts[0].applied_plan_id == 7


@pytest.mark.asyncio
async def test_cleanup_is_idempotent_and_removes_exercises_and_sets(db_factory):
    await seed(db_factory)
    async with db_factory() as db:
        db.add(Workout(user_id="another-user", name="Keep", applied_plan_id=7, workout_type="generated"))
        await db.commit()
    with patch("workouts_service.routers.internal_purge.settings") as settings:
        settings.INTERNAL_GATEWAY_SECRET = "test-secret"
        async with db_factory() as db:
            assert await cleanup_failed_application("user-1", 7, db, "test-secret") == {"deleted": 1, "detached": 0}
        async with db_factory() as db:
            assert await cleanup_failed_application("user-1", 7, db, "test-secret") == {"deleted": 0, "detached": 0}
        async with db_factory() as db:
            assert list((await db.execute(select(WorkoutSet))).scalars()) == []
            assert list((await db.execute(select(WorkoutExercise))).scalars()) == []
            remaining = (await db.execute(select(Workout))).scalar_one()
            assert remaining.user_id == "another-user"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "completed_at"),
    [("completed", None), ("pending", datetime(2026, 11, 10, tzinfo=UTC))],
)
async def test_legacy_shift_keeps_completed_workout(db_factory, status, completed_at):
    await seed(db_factory, status=status, completed_at=completed_at)
    async with db_factory() as db:
        result = await WorkoutService(db, None, user_id="user-1").shift_schedule_in_plan(
            applied_plan_id=7, from_order_index=0, delta_days=3, delta_index=1, only_future=False
        )
        assert result["affected_count"] == 0
        workout = (await db.execute(select(Workout))).scalar_one()
        assert workout.plan_order_index == 0
