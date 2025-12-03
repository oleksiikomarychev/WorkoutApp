from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_user_id, get_db
from ..schemas.coach_planning import (
    CoachExerciseInstanceCreate,
    CoachExerciseInstanceUpdate,
    CoachWorkoutUpdate,
)
from ..services.coach_planning_service import (
    create_exercise_instance_for_athlete,
    delete_exercise_instance_for_athlete,
    get_active_plan_analytics_for_athlete,
    get_active_plan_for_athlete,
    get_active_plan_workouts_for_athlete,
    update_exercise_instance_for_athlete,
    update_workout_for_athlete,
)

router = APIRouter(prefix="/crm/coach", tags=["crm-coach"])


@router.get("/athletes/{athlete_id}/active-plan")
async def coach_get_active_plan(
    athlete_id: str,
    coach_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await get_active_plan_for_athlete(db=db, coach_id=coach_id, athlete_id=athlete_id)


@router.get("/athletes/{athlete_id}/active-plan/analytics")
async def coach_get_active_plan_analytics(
    athlete_id: str,
    group_by: str | None = Query(None, regex="^(order|date)$"),
    coach_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await get_active_plan_analytics_for_athlete(
        db=db,
        coach_id=coach_id,
        athlete_id=athlete_id,
        group_by=group_by,
    )


@router.get("/athletes/{athlete_id}/active-plan/workouts")
async def coach_get_active_plan_workouts(
    athlete_id: str,
    coach_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await get_active_plan_workouts_for_athlete(db=db, coach_id=coach_id, athlete_id=athlete_id)


@router.patch("/athletes/{athlete_id}/workouts/{workout_id}")
async def coach_update_workout(
    athlete_id: str,
    workout_id: int,
    payload: CoachWorkoutUpdate,
    coach_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    body = payload.model_dump(mode="json", exclude_none=True)
    if not body:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Nothing to update")
    return await update_workout_for_athlete(
        db=db,
        coach_id=coach_id,
        athlete_id=athlete_id,
        workout_id=workout_id,
        payload=body,
    )


@router.patch("/athletes/{athlete_id}/exercises/{instance_id}")
async def coach_update_exercise_instance(
    athlete_id: str,
    instance_id: int,
    payload: CoachExerciseInstanceUpdate,
    coach_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    body = payload.model_dump(mode="json", exclude_none=True)
    if not body:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Nothing to update")
    return await update_exercise_instance_for_athlete(
        db=db,
        coach_id=coach_id,
        athlete_id=athlete_id,
        instance_id=instance_id,
        payload=body,
    )


@router.post("/athletes/{athlete_id}/workouts/{workout_id}/exercises", status_code=status.HTTP_201_CREATED)
async def coach_create_exercise_instance(
    athlete_id: str,
    workout_id: int,
    payload: CoachExerciseInstanceCreate,
    coach_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    body = payload.model_dump(mode="json", exclude_none=True)
    return await create_exercise_instance_for_athlete(
        db=db,
        coach_id=coach_id,
        athlete_id=athlete_id,
        workout_id=workout_id,
        payload=body,
    )


@router.delete("/athletes/{athlete_id}/exercises/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def coach_delete_exercise_instance(
    athlete_id: str,
    instance_id: int,
    coach_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await delete_exercise_instance_for_athlete(
        db=db,
        coach_id=coach_id,
        athlete_id=athlete_id,
        instance_id=instance_id,
    )
