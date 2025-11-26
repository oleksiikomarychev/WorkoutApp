"""Shared Redis client and cache key helpers for plans-service."""

from __future__ import annotations

from typing import Iterable, Optional

import structlog
from redis.asyncio import Redis

from .config import get_settings

logger = structlog.get_logger(__name__)

redis_client: Optional[Redis] = None

PLAN_DETAIL_TTL_SECONDS = 15 * 60  # 15 minutes
PLAN_LIST_TTL_SECONDS = 5 * 60  # 5 minutes
FAVORITE_PLANS_TTL_SECONDS = 5 * 60  # 5 minutes


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
    """Initialize global Redis client if configuration is present."""
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
    except Exception as exc:
        logger.error("redis_connection_failed", error=str(exc))
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
        logger.info("redis_connection_closed")
    except Exception as exc:
        logger.warning("redis_close_failed", error=str(exc))
    finally:
        redis_client = None


async def invalidate_plans_cache(user_id: str, plan_ids: Optional[Iterable[int]] = None) -> None:
    """Remove cached plan data and list aggregates for a user."""
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
    except Exception as exc:
        logger.warning("plans_cache_invalidation_failed", keys=list(keys), error=str(exc))
