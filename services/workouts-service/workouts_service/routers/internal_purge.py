import os

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Workout
from ..redis_client import get_redis

router = APIRouter(prefix="/internal/users", tags=["internal"])


@router.post("/{user_id}/purge")
async def purge_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    x_internal_secret: str | None = Header(None, alias="X-Internal-Secret"),
) -> dict[str, str]:
    expected_secret = (os.getenv("INTERNAL_GATEWAY_SECRET") or "").strip()
    if not expected_secret or x_internal_secret != expected_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

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
