from __future__ import annotations

from collections.abc import Iterable

import structlog
from redis.asyncio import Redis

from .config import get_settings

logger = structlog.get_logger(__name__)

redis_client: Redis | None = None

PLAN_DETAIL_TTL_SECONDS = 15 * 60
PLAN_LIST_TTL_SECONDS = 5 * 60
FAVORITE_PLANS_TTL_SECONDS = 5 * 60


def calendar_plan_key(user_id: str, plan_id: int) -> str:
    return f"plans:calendar:{user_id}:{plan_id}"


def plans_list_key(user_id: str, roots_only: bool) -> str:
    flag = "true" if roots_only else "false"
    return f"plans:list:{user_id}:roots:{flag}"


def favorite_plans_key(user_id: str) -> str:
    return f"plans:favorites:{user_id}"


def applied_plan_key(user_id: str) -> str:
    return f"plans:applied:active:{user_id}"


async def init_redis() -> None:
    global redis_client

    settings = get_settings()
    try:
        redis_client = Redis(
            host=settings.PLANS_REDIS_HOST,
            port=settings.PLANS_REDIS_PORT,
            db=settings.PLANS_REDIS_DB,
            password=settings.PLANS_REDIS_PASSWORD,
            encoding="utf-8",
            decode_responses=True,
            health_check_interval=30,
        )
        await redis_client.ping()
        logger.info(
            "redis_connection_established",
            host=settings.PLANS_REDIS_HOST,
            port=settings.PLANS_REDIS_PORT,
            db=settings.PLANS_REDIS_DB,
        )
    except Exception:
        logger.error("Failed to connect to plans redis", exc_info=True)
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
        logger.info("redis_connection_closed")
    except Exception:
        logger.warning("Failed to close plans redis connection", exc_info=True)
    finally:
        redis_client = None


async def invalidate_plans_cache(user_id: str, plan_ids: Iterable[int] | None = None) -> None:
    if redis_client is None:
        return

    keys: set[str] = set()
    if plan_ids:
        for plan_id in plan_ids:
            if plan_id is None:
                continue
            keys.add(calendar_plan_key(user_id, int(plan_id)))

    keys.add(plans_list_key(user_id, True))
    keys.add(plans_list_key(user_id, False))
    keys.add(favorite_plans_key(user_id))

    keys = {key for key in keys if key}
    if not keys:
        return

    try:
        await redis_client.delete(*keys)
    except Exception:
        logger.warning("Failed to invalidate plans cache", keys=list(keys), exc_info=True)
