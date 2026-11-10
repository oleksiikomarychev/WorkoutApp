"""Ownership metadata needed for client-side destructive action visibility."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from plans_service.schemas.calendar_plan import CalendarPlanResponse
from plans_service.services.calendar_plan_service import CalendarPlanService


def test_plan_response_preserves_owner():
    plan = SimpleNamespace(
        id=7, name="Original", user_id="owner", duration_weeks=12,
        is_active=True, root_plan_id=7, mesocycles=[],
    )
    response = CalendarPlanService._get_plan_response(plan)
    assert response.user_id == "owner"
    assert CalendarPlanResponse.model_validate_json(response.model_dump_json()).user_id == "owner"


def test_old_cached_response_has_no_assumed_owner():
    response = CalendarPlanResponse(
        id=7, name="Original", duration_weeks=12, is_active=True, root_plan_id=7,
    )
    assert response.user_id is None


@pytest.mark.asyncio
async def test_detail_rebuilds_legacy_cache_with_owner():
    legacy = CalendarPlanResponse(
        id=7, name="Original", duration_weeks=12, is_active=True, root_plan_id=7,
    )
    redis = AsyncMock()
    redis.get.return_value = legacy.model_dump_json()
    plan = SimpleNamespace(
        id=7, name="Original", user_id="owner", duration_weeks=12,
        is_active=True, root_plan_id=7, mesocycles=[],
    )
    result = MagicMock()
    result.scalars.return_value.first.return_value = plan
    db = AsyncMock()
    db.execute.return_value = result
    with patch('plans_service.services.calendar_plan_service.get_redis', return_value=redis):
        response = await CalendarPlanService.get_plan(db, 7, 'owner')
    assert response.user_id == 'owner'
    db.execute.assert_awaited_once()
    redis.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_denied_when_owner_query_does_not_match():
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = None
    db.execute.return_value = result
    with pytest.raises(HTTPException) as exc:
        await CalendarPlanService.delete_plan(db, 7, 'visitor')
    assert exc.value.status_code == 404
    statement = db.execute.call_args.args[0]
    assert 'calendar_plans.user_id' in str(statement)
    assert 'visitor' in statement.compile().params.values()
    db.commit.assert_not_awaited()
