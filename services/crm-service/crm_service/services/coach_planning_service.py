from __future__ import annotations

import json
from typing import Any

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..metrics import (
    CRM_EXERCISE_UPDATES_TOTAL,
    CRM_MASS_EDIT_REQUESTS_TOTAL,
    CRM_WORKOUT_UPDATES_TOTAL,
)
from ..models.relationships import CoachAthleteLink
from ..schemas.coach_planning import CoachWorkoutsMassEditRequest
from .relationships_service import _log_coach_athlete_event


class CoachAthleteLinkInactiveError(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail="Coach-athlete link inactive")


async def _ensure_active_link(db: AsyncSession, coach_id: str, athlete_id: str) -> CoachAthleteLink:
    stmt = select(CoachAthleteLink).where(
        CoachAthleteLink.coach_id == coach_id,
        CoachAthleteLink.athlete_id == athlete_id,
        CoachAthleteLink.status == "active",
    )
    res = await db.execute(stmt)
    link = res.scalar_one_or_none()
    if not link:
        raise CoachAthleteLinkInactiveError()
    return link


async def _proxy_request_for_athlete(
    method: str,
    base_url: str,
    path: str,
    athlete_id: str,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> Any:
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    headers = {"X-User-Id": athlete_id}
    timeout = httpx.Timeout(10.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=json_body,
            follow_redirects=True,
        )
    if resp.status_code >= 400:
        detail = resp.text
        try:
            detail_json = resp.json()
            detail = json.dumps(detail_json)
        except Exception:
            pass
        raise HTTPException(status_code=resp.status_code, detail=detail)
    try:
        return resp.json()
    except Exception:
        return None


async def get_active_plan_for_athlete(
    db: AsyncSession,
    coach_id: str,
    athlete_id: str,
) -> Any:
    await _ensure_active_link(db, coach_id=coach_id, athlete_id=athlete_id)
    return await _proxy_request_for_athlete(
        method="GET",
        base_url=settings.plans_service_url,
        path="/applied-plans/active",
        athlete_id=athlete_id,
    )


async def get_active_plan_workouts_for_athlete(
    db: AsyncSession,
    coach_id: str,
    athlete_id: str,
) -> list[Any]:
    plan = await get_active_plan_for_athlete(db=db, coach_id=coach_id, athlete_id=athlete_id)
    if not isinstance(plan, dict) or not plan.get("id"):
        return []
    applied_plan_id = plan["id"]
    data = await _proxy_request_for_athlete(
        method="GET",
        base_url=settings.workouts_service_url,
        path="/workouts",
        athlete_id=athlete_id,
        params={"applied_plan_id": applied_plan_id},
    )
    if isinstance(data, list):
        return data
    return []


async def update_workout_for_athlete(
    db: AsyncSession,
    coach_id: str,
    athlete_id: str,
    workout_id: int,
    payload: dict[str, Any],
) -> Any:
    link = await _ensure_active_link(db, coach_id=coach_id, athlete_id=athlete_id)
    data = await _proxy_request_for_athlete(
        method="PATCH",
        base_url=settings.workouts_service_url,
        path=f"/workouts/{workout_id}",
        athlete_id=athlete_id,
        json_body=payload,
    )
    _log_coach_athlete_event(
        db=db,
        link_id=link.id,
        actor_id=coach_id,
        event_type="workout_updated",
        payload={"workout_id": workout_id, "fields": list(payload.keys())},
    )
    await db.commit()
    CRM_WORKOUT_UPDATES_TOTAL.inc()
    return data


async def update_exercise_instance_for_athlete(
    db: AsyncSession,
    coach_id: str,
    athlete_id: str,
    instance_id: int,
    payload: dict[str, Any],
) -> Any:
    link = await _ensure_active_link(db, coach_id=coach_id, athlete_id=athlete_id)
    data = await _proxy_request_for_athlete(
        method="PATCH",
        base_url=settings.exercises_service_url,
        path=f"/exercises/instances/{instance_id}",
        athlete_id=athlete_id,
        json_body=payload,
    )
    _log_coach_athlete_event(
        db=db,
        link_id=link.id,
        actor_id=coach_id,
        event_type="exercise_instance_updated",
        payload={"instance_id": instance_id, "fields": list(payload.keys())},
    )
    await db.commit()
    CRM_EXERCISE_UPDATES_TOTAL.inc()
    return data


async def mass_edit_workouts_for_athlete(
    db: AsyncSession,
    coach_id: str,
    athlete_id: str,
    request: CoachWorkoutsMassEditRequest,
) -> dict[str, Any]:
    await _ensure_active_link(db, coach_id=coach_id, athlete_id=athlete_id)

    workout_results: list[Any] = []
    exercise_results: list[Any] = []

    for item in request.workouts or []:
        body = item.update.model_dump(exclude_none=True)
        if not body:
            continue
        result = await update_workout_for_athlete(
            db=db,
            coach_id=coach_id,
            athlete_id=athlete_id,
            workout_id=item.workout_id,
            payload=body,
        )
        workout_results.append(result)

    for item in request.exercise_instances or []:
        body = item.update.model_dump(exclude_none=True)
        if not body:
            continue
        result = await update_exercise_instance_for_athlete(
            db=db,
            coach_id=coach_id,
            athlete_id=athlete_id,
            instance_id=item.instance_id,
            payload=body,
        )
        exercise_results.append(result)

    total_updates = len(workout_results) + len(exercise_results)
    if total_updates:
        CRM_MASS_EDIT_REQUESTS_TOTAL.inc(total_updates)
    return {"workouts": workout_results, "exercise_instances": exercise_results}
