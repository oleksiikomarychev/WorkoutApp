from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from workouts_service.routers.internal_purge import cleanup_failed_application


@pytest.mark.asyncio
async def test_cleanup_detaches_started_workout_without_deleting():
    workout = SimpleNamespace(
        id=11, started_at=object(), completed_at=None, status="in_progress", sessions=[], applied_plan_id=7
    )
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [workout]
    db.execute.return_value = result
    with patch("workouts_service.routers.internal_purge.settings") as settings:
        settings.INTERNAL_GATEWAY_SECRET = "test-secret"
        with patch("workouts_service.routers.internal_purge.invalidate_workout_cache", new_callable=AsyncMock):
            response = await cleanup_failed_application("user-1", 7, db, "test-secret")
    assert response == {"deleted": 0, "detached": 1}
    assert workout.applied_plan_id is None
    db.delete.assert_not_awaited()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_cleanup_deletes_only_selected_unstarted_workouts():
    workout = SimpleNamespace(id=11, started_at=None, completed_at=None, status="pending", sessions=[])
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [workout]
    db.execute.return_value = result
    with patch("workouts_service.routers.internal_purge.settings") as settings:
        settings.INTERNAL_GATEWAY_SECRET = "test-secret"
        with patch("workouts_service.routers.internal_purge.invalidate_workout_cache", new_callable=AsyncMock):
            response = await cleanup_failed_application("user-1", 7, db, "test-secret")
    assert response == {"deleted": 1, "detached": 0}
    db.delete.assert_awaited_once_with(workout)
    db.commit.assert_awaited_once()
    sql = str(db.execute.call_args.args[0])
    assert "applied_plan_id" in sql and "user_id" in sql
