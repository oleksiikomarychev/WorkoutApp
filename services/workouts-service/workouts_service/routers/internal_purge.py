from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import settings
from ..database import get_db
from ..models import Workout, WorkoutSession
from ..redis_client import get_redis, invalidate_workout_cache

router = APIRouter(prefix="/internal/users", tags=["internal"])


@router.post("/{user_id}/applied-plans/{applied_plan_id}/cleanup")
async def cleanup_failed_application(
    user_id: str,
    applied_plan_id: int,
    db: AsyncSession = Depends(get_db),
    x_internal_secret: str | None = Header(None, alias="X-Internal-Secret"),
) -> dict[str, int]:
    expected_secret = (settings.INTERNAL_GATEWAY_SECRET or "").strip()
    if not expected_secret or x_internal_secret != expected_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    result = await db.execute(
        select(Workout)
        .where(Workout.user_id == user_id, Workout.applied_plan_id == applied_plan_id)
        .options(selectinload(Workout.sessions))
        .with_for_update()
    )
    workouts = list(result.scalars().all())
    ids = [int(w.id) for w in workouts]
    detached = 0
    for workout in workouts:
        if (
            workout.started_at is not None
            or workout.completed_at is not None
            or workout.status == "completed"
            or workout.sessions
        ):
            workout.applied_plan_id = None
            workout.plan_order_index = None
            workout.microcycle_id = None
            detached += 1
        else:
            await db.delete(workout)
    await db.commit()
    if ids:
        await invalidate_workout_cache(user_id, workout_ids=ids)
    return {"deleted": len(ids) - detached, "detached": detached}


@router.post("/{user_id}/purge")
async def purge_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    x_internal_secret: str | None = Header(None, alias="X-Internal-Secret"),
) -> dict[str, str]:
    expected_secret = (settings.INTERNAL_GATEWAY_SECRET or "").strip()
    if not expected_secret or x_internal_secret != expected_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    await db.execute(delete(WorkoutSession).where(WorkoutSession.user_id == user_id))
    await db.execute(delete(Workout).where(Workout.user_id == user_id))
    await db.commit()

    redis = await get_redis()
    if redis is not None:
        patterns = (
            f"workouts:detail:{user_id}:*",
            f"workouts:list:{user_id}:*",
            f"workouts:session:{user_id}:*",
        )
        keys: list[str] = [f"workouts:session:list:{user_id}"]
        for pattern in patterns:
            async for key in redis.scan_iter(match=pattern, count=500):
                if isinstance(key, str):
                    keys.append(key)
                else:
                    keys.append(key.decode("utf-8", errors="ignore"))
        if keys:
            try:
                await redis.delete(*keys)
            except Exception:
                pass
    return {"status": "ok"}
