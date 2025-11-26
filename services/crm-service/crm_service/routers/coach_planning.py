from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_user_id, get_db
from ..schemas.coach_planning import (
    CoachExerciseInstanceUpdate,
    CoachWorkoutUpdate,
)
from ..services.coach_planning_service import (
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
    body = payload.model_dump(exclude_none=True)
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
    body = payload.model_dump(exclude_none=True)
    if not body:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Nothing to update")
    return await update_exercise_instance_for_athlete(
        db=db,
        coach_id=coach_id,
        athlete_id=athlete_id,
        instance_id=instance_id,
        payload=body,
    )
