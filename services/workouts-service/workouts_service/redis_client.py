"""Redis client utilities for workouts-service."""

from __future__ import annotations

from typing import Iterable, Optional

import structlog
from redis.asyncio import Redis

from .config import get_settings

logger = structlog.get_logger(__name__)

redis_client: Optional[Redis] = None

WORKOUT_DETAIL_TTL_SECONDS = 10 * 60  # 10 minutes for individual workouts
WORKOUT_LIST_TTL_SECONDS = 5 * 60  # 5 minutes for workout lists per user
SESSION_DETAIL_TTL_SECONDS = 5 * 60  # 5 minutes for session details


def workout_detail_key(user_id: str, workout_id: int) -> str:
    return f"workouts:detail:{user_id}:{workout_id}"


def workout_list_key(user_id: str, status: str | None = None) -> str:
    suffix = status if status else "all"
    return f"workouts:list:{user_id}:{suffix}"


def session_detail_key(user_id: str, session_id: int) -> str:
    return f"workouts:session:{user_id}:{session_id}"


def session_list_key(user_id: str) -> str:
    return f"workouts:session:list:{user_id}"


async def init_redis() -> None:
    global redis_client

    settings = get_settings()
    try:
        redis_client = Redis(
            host=settings.WORKOUTS_REDIS_HOST,
            port=settings.WORKOUTS_REDIS_PORT,
            db=settings.WORKOUTS_REDIS_DB,
            password=settings.WORKOUTS_REDIS_PASSWORD,
            encoding="utf-8",
            decode_responses=True,
            health_check_interval=30,
        )
        await redis_client.ping()
        logger.info(
            "workouts_redis_connected",
            host=settings.WORKOUTS_REDIS_HOST,
            port=settings.WORKOUTS_REDIS_PORT,
            db=settings.WORKOUTS_REDIS_DB,
        )
    except Exception as exc:
        logger.error("workouts_redis_connection_failed", error=str(exc))
        redis_client = None


async def get_redis() -> Optional[Redis]:
    return redis_client


async def close_redis() -> None:
    global redis_client

    if redis_client is None:
        return

    try:
        await redis_client.close()
        await redis_client.connection_pool.disconnect()
        logger.info("workouts_redis_closed")
    except Exception as exc:
        logger.warning("workouts_redis_close_failed", error=str(exc))
    finally:
        redis_client = None


async def invalidate_workout_cache(
    user_id: str,
    workout_ids: Optional[Iterable[int]] = None,
    invalidate_lists: bool = True,
) -> None:
    if redis_client is None:
        return

    keys: set[str] = set()
    if workout_ids:
        for workout_id in workout_ids:
            if workout_id is None:
                continue
            keys.add(workout_detail_key(user_id, int(workout_id)))

    if invalidate_lists:
        keys.add(workout_list_key(user_id, None))

    if not keys:
        return

    try:
        await redis_client.delete(*keys)
    except Exception as exc:
        logger.warning("workouts_cache_invalidation_failed", keys=list(keys), error=str(exc))


async def invalidate_session_cache(
    user_id: str,
    session_ids: Optional[Iterable[int]] = None,
) -> None:
    if redis_client is None:
        return

    keys: set[str] = {session_list_key(user_id)}
    if session_ids:
        for session_id in session_ids:
            if session_id is None:
                continue
            keys.add(session_detail_key(user_id, int(session_id)))

    try:
        await redis_client.delete(*keys)
    except Exception as exc:
        logger.warning("workouts_session_cache_invalidation_failed", keys=list(keys), error=str(exc))
