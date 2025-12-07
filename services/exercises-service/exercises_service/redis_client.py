from __future__ import annotations

from collections.abc import Iterable

import structlog
from redis.asyncio import Redis

from .config import get_settings

logger = structlog.get_logger(__name__)

redis_client: Redis | None = None

EXERCISE_DEF_TTL_SECONDS = 60 * 60
EXERCISE_LIST_TTL_SECONDS = 30 * 60
EXERCISE_INSTANCE_TTL_SECONDS = 10 * 60
EXERCISE_WORKOUT_TTL_SECONDS = 5 * 60


def exercise_definition_key(definition_id: int) -> str:
    return f"exercises:def:{definition_id}"


def exercise_definitions_list_key(ids: tuple[int, ...] | None) -> str:
    if not ids:
        return "exercises:def:list:all"
    normalized = ",".join(str(item) for item in ids)
    return f"exercises:def:list:{normalized}"


def exercise_instance_key(user_id: str, instance_id: int) -> str:
    return f"exercises:instance:{user_id}:{instance_id}"


def workout_instances_key(user_id: str, workout_id: int) -> str:
    return f"exercises:workout:{user_id}:{workout_id}:instances"


async def init_redis() -> None:
    global redis_client

    settings = get_settings()
    try:
        redis_client = Redis(
            host=settings.EXERCISES_REDIS_HOST,
            port=settings.EXERCISES_REDIS_PORT,
            db=settings.EXERCISES_REDIS_DB,
            password=settings.EXERCISES_REDIS_PASSWORD,
            encoding="utf-8",
            decode_responses=True,
            health_check_interval=30,
        )
        await redis_client.ping()
        logger.info(
            "exercises_redis_connected",
            host=settings.EXERCISES_REDIS_HOST,
            port=settings.EXERCISES_REDIS_PORT,
            db=settings.EXERCISES_REDIS_DB,
        )
    except Exception:
        logger.error("Failed to connect to exercises redis", exc_info=True)
        redis_client = None


async def get_redis() -> Redis | None:
    return redis_client


async def close_redis() -> None:
    global redis_client

    if redis_client is None:
        return

    try:
        await redis_client.close()
        await redis_client.connection_pool.disconnect()
        logger.info("exercises_redis_closed")
    except Exception:
        logger.warning("Failed to close exercises redis connection", exc_info=True)
    finally:
        redis_client = None


async def invalidate_exercise_cache(
    definition_ids: Iterable[int] | None = None,
    invalidate_lists: bool = True,
) -> None:
    if redis_client is None:
        return

    keys: set[str] = set()
    if definition_ids:
        for definition_id in definition_ids:
            if definition_id is None:
                continue
            keys.add(exercise_definition_key(int(definition_id)))

    if invalidate_lists:
        keys.add(exercise_definitions_list_key(None))

    if not keys:
        return

    try:
        await redis_client.delete(*keys)
    except Exception:
        logger.warning("Failed to invalidate exercise cache", keys=list(keys), exc_info=True)


async def invalidate_instance_cache(
    user_id: str,
    instance_ids: Iterable[int] | None = None,
    workout_ids: Iterable[int] | None = None,
) -> None:
    if redis_client is None:
        return

    keys: set[str] = set()
    if instance_ids:
        for instance_id in instance_ids:
            if instance_id is None:
                continue
            keys.add(exercise_instance_key(user_id, int(instance_id)))

    if workout_ids:
        for workout_id in workout_ids:
            if workout_id is None:
                continue
            keys.add(workout_instances_key(user_id, int(workout_id)))

    if not keys:
        return

    try:
        await redis_client.delete(*keys)
    except Exception:
        logger.warning("Failed to invalidate exercise instance cache", keys=list(keys), exc_info=True)
