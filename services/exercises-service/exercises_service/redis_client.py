from __future__ import annotations

import hashlib
import json
from collections.abc import AsyncGenerator, Iterable
from contextlib import asynccontextmanager
from typing import Any

import redis.asyncio as redis
import structlog

from .config import get_settings

logger = structlog.get_logger(__name__)

EXERCISE_DEF_TTL_SECONDS = 60 * 60
EXERCISE_LIST_TTL_SECONDS = 30 * 60
EXERCISE_WORKOUT_TTL_SECONDS = 5 * 60

EXERCISE_HOT_TTL = 300
EXERCISE_WARM_TTL = 900
EXERCISE_COLD_TTL = 2700
EXERCISE_LIST_TTL = 1200


def exercise_definition_key(definition_id: int) -> str:
    """Return Redis key for a single exercise definition."""
    return f"exercises:def:{definition_id}"


def exercise_definitions_list_key(ids: tuple[int, ...] | None) -> str:
    """Return Redis key for a list of exercise definitions."""
    if not ids:
        return "exercises:def:list:all"
    normalized = ",".join(str(item) for item in ids)
    return f"exercises:def:list:{normalized}"


def hot_exercise_key(exercise_id: int) -> str:
    return f"exercises:hot:{exercise_id}"


def hot_exercises_list_key() -> str:
    return "exercises:hot:list"


def warm_exercise_key(exercise_id: int) -> str:
    return f"exercises:warm:{exercise_id}"


def warm_exercises_list_key() -> str:
    return "exercises:warm:list"


def cold_exercise_key(exercise_id: int) -> str:
    return f"exercises:cold:{exercise_id}"


def cold_exercises_list_key() -> str:
    return "exercises:cold:list"


def search_cache_key(search_query: str, filters_hash: str = "") -> str:
    search_hash = hashlib.md5(f"{search_query}:{filters_hash}".encode()).hexdigest()[:8]
    return f"exercises:search:{search_hash}"


def filtered_cache_key(filters_hash: str) -> str:
    return f"exercises:filtered:{filters_hash}"


def generate_filters_hash(
    muscle_groups: list[str] | None = None,
    equipment_types: list[str] | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> str:
    """Generate a stable 8-character MD5 hash representing query filter parameters."""
    mg_part = ",".join(muscle_groups or [])
    eq_part = ",".join(equipment_types or [])
    filter_str = f"mg:{mg_part}:eq:{eq_part}:limit={limit}:offset={offset}"
    return hashlib.md5(filter_str.encode()).hexdigest()[:8]


def workout_instances_key(user_id: str, workout_id: int) -> str:
    return f"exercises:workout:{user_id}:{workout_id}:instances"


class RedisClient:
    """Async Redis client wrapper with connection pooling and caching helpers."""

    def __init__(self) -> None:
        self._client: redis.Redis | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize Redis connection pool and verify connectivity."""
        if self._initialized and self._client is not None:
            return

        settings = get_settings()
        try:
            pool = redis.ConnectionPool(
                host=settings.EXERCISES_REDIS_HOST,
                port=settings.EXERCISES_REDIS_PORT,
                db=settings.EXERCISES_REDIS_DB,
                password=settings.EXERCISES_REDIS_PASSWORD,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
                retry_on_timeout=True,
                health_check_interval=30,
            )
            self._client = redis.Redis(connection_pool=pool)
            await self._client.ping()
            self._initialized = True
            logger.info(
                "exercises_redis_connected",
                host=settings.EXERCISES_REDIS_HOST,
                port=settings.EXERCISES_REDIS_PORT,
                db=settings.EXERCISES_REDIS_DB,
                max_connections=20,
            )
        except Exception:
            logger.warning("Failed to connect to exercises redis", exc_info=True)
            self._client = None
            self._initialized = False

    @property
    def client(self) -> redis.Redis | None:
        return self._client

    def is_connected(self) -> bool:
        return self._initialized and self._client is not None

    async def close(self) -> None:
        """Close connection pool cleanly."""
        if self._client is None:
            return

        try:
            await self._client.close()
            await self._client.connection_pool.disconnect()
            logger.info("exercises_redis_closed")
        except Exception:
            logger.warning("Failed to close exercises redis connection", exc_info=True)
        finally:
            self._client = None
            self._initialized = False

    async def invalidate_exercise_cache(
        self,
        definition_ids: Iterable[int] | None = None,
        invalidate_lists: bool = True,
        specific_list_keys: list[str] | None = None,
    ) -> None:
        """Invalidate single exercise definitions and cached lists."""
        if not self.is_connected() or self._client is None:
            return

        keys: set[str] = set()

        if definition_ids:
            for definition_id in definition_ids:
                if definition_id is not None:
                    keys.add(exercise_definition_key(int(definition_id)))

        if invalidate_lists:
            if specific_list_keys:
                keys.update(specific_list_keys)
            else:
                keys.add(exercise_definitions_list_key(None))

        if not keys:
            return

        try:
            pipe = self._client.pipeline()
            for key in keys:
                pipe.delete(key)
            await pipe.execute()
            logger.info("Invalidated exercise cache", keys_count=len(keys))
        except Exception:
            logger.warning("Failed to invalidate exercise cache", keys=list(keys), exc_info=True)

    async def get_exercise_from_smart_cache(self, exercise_id: int) -> dict[str, Any] | None:
        """Get cached exercise definition dictionary with TTL refreshment."""
        if not self.is_connected() or self._client is None:
            return None

        cache_key = exercise_definition_key(exercise_id)
        cached_data = await self._client.get(cache_key)

        if cached_data:
            ttl = await self._client.ttl(cache_key)
            # If remaining TTL is low, extend it to keep warm items cached
            if ttl < 300:
                await self._client.expire(cache_key, EXERCISE_WARM_TTL)

            try:
                return json.loads(cached_data) if isinstance(cached_data, str) else cached_data
            except Exception:
                return None

        return None

    async def set_exercise_in_smart_cache(self, exercise_id: int, data: dict[str, Any] | str) -> None:
        """Set cached exercise definition with JSON serialization."""
        if not self.is_connected() or self._client is None:
            return

        cache_key = exercise_definition_key(exercise_id)
        serialized = json.dumps(data) if isinstance(data, dict) else str(data)
        await self._client.setex(cache_key, EXERCISE_WARM_TTL, serialized)

    async def get_smart_exercise_list(
        self,
        muscle_groups: list[str] | None = None,
        equipment_types: list[str] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]] | None:
        """Get cached list of exercise definitions matching filter criteria."""
        if not self.is_connected() or self._client is None:
            return None

        filters_hash = generate_filters_hash(muscle_groups, equipment_types, limit, offset)
        cache_key = filtered_cache_key(filters_hash)

        cached_data = await self._client.get(cache_key)
        if cached_data:
            ttl = await self._client.ttl(cache_key)
            if ttl < 600:
                await self._client.expire(cache_key, EXERCISE_LIST_TTL)
            try:
                return json.loads(cached_data)
            except Exception:
                return None

        return None

    async def set_smart_exercise_list(
        self,
        exercises: list[dict[str, Any]],
        muscle_groups: list[str] | None = None,
        equipment_types: list[str] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> None:
        """Cache filtered list of exercise definitions as JSON."""
        if not self.is_connected() or self._client is None:
            return

        filters_hash = generate_filters_hash(muscle_groups, equipment_types, limit, offset)
        cache_key = filtered_cache_key(filters_hash)
        serialized_exercises = json.dumps(exercises)
        await self._client.setex(cache_key, EXERCISE_LIST_TTL, serialized_exercises)


_redis_client = RedisClient()


async def get_redis_client() -> RedisClient:
    """FastAPI dependency to retrieve shared RedisClient instance."""
    if not _redis_client.is_connected():
        await _redis_client.initialize()
    return _redis_client


async def init_redis() -> None:
    """Initialize Redis client on application startup."""
    await _redis_client.initialize()


async def close_redis() -> None:
    """Close Redis client on application shutdown."""
    await _redis_client.close()


@asynccontextmanager
async def redis_client_context() -> AsyncGenerator[RedisClient, None]:
    """Context manager for using RedisClient in standalone scripts."""
    await _redis_client.initialize()
    try:
        yield _redis_client
    finally:
        await _redis_client.close()
