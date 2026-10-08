from __future__ import annotations

import json
from collections.abc import AsyncGenerator, Iterable
from contextlib import asynccontextmanager

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
    return f"exercises:def:{definition_id}"


def exercise_definitions_list_key(ids: tuple[int, ...] | None) -> str:
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
    import hashlib
    search_hash = hashlib.md5(f"{search_query}:{filters_hash}".encode()).hexdigest()[:8]
    return f"exercises:search:{search_hash}"


def filtered_cache_key(filters_hash: str) -> str:
    return f"exercises:filtered:{filters_hash}"


def generate_filters_hash(
    muscle_groups: list[str] | None = None,
    equipment_types: list[str] | None = None,
    limit: int | None = None,
    offset: int = 0
) -> str:
    import hashlib
    filter_str = f"mg:{','.join(muscle_groups or [])}:eq:{','.join(equipment_types or [])}:limit={limit}:offset={offset}"
    return hashlib.md5(filter_str.encode()).hexdigest()[:8]


def workout_instances_key(user_id: str, workout_id: int) -> str:
    return f"exercises:workout:{user_id}:{workout_id}:instances"


class RedisClient:
    def __init__(self):
        self._client: redis.Redis | None = None
        self._initialized = False

    async def initialize(self) -> None:
        if self._initialized:
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
            logger.error("Failed to connect to exercises redis", exc_info=True)
            self._client = None
            self._initialized = False

    @property
    def client(self) -> redis.Redis | None:
        return self._client

    def is_connected(self) -> bool:
        return self._initialized and self._client is not None

    async def close(self) -> None:
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
        if not self.is_connected():
            return

        keys: set[str] = set()
        
        # Invalidate specific definition keys (single key per exercise now)
        if definition_ids:
            for definition_id in definition_ids:
                if definition_id is None:
                    continue
                keys.add(exercise_definition_key(int(definition_id)))

        # Invalidate list cache
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

    async def get_exercise_from_smart_cache(self, exercise_id: int) -> dict | None:
        """Get exercise using single cache key with TTL-based aging"""
        if not self.is_connected():
            return None
        
        cache_key = exercise_definition_key(exercise_id)
        cached_data = await self._client.get(cache_key)
        
        if cached_data:
            ttl = await self._client.ttl(cache_key)
            
            if ttl < 300:
                await self._client.expire(cache_key, EXERCISE_WARM_TTL)
            elif ttl < 900:  
                await self._client.expire(cache_key, EXERCISE_HOT_TTL)
            
            return cached_data
        
        return None

    async def set_exercise_in_smart_cache(self, exercise_id: int, data: dict) -> None:
        if not self.is_connected():
            return
        
        cache_key = exercise_definition_key(exercise_id)
        await self._client.setex(cache_key, EXERCISE_WARM_TTL, data)

    async def get_smart_exercise_list(
        self,
        muscle_groups: list[str] | None = None,
        equipment_types: list[str] | None = None,
        limit: int = 50,
        offset: int = 0
    ) -> list[dict] | None:
        if not self.is_connected():
            return None
        
        filters_hash = generate_filters_hash(muscle_groups, equipment_types, limit, offset)
        cache_key = filtered_cache_key(filters_hash)
        
        cached_data = await self._client.get(cache_key)
        if cached_data:
            ttl = await self._client.ttl(cache_key)
            if ttl < 600:
                await self._client.expire(cache_key, EXERCISE_LIST_TTL)
            return json.loads(cached_data)
        
        return None

    async def set_smart_exercise_list(
        self,
        exercises: list[dict],
        muscle_groups: list[str] | None = None,
        equipment_types: list[str] | None = None,
        limit: int = 50,
        offset: int = 0
    ) -> None:
        if not self.is_connected():
            return
        
        filters_hash = generate_filters_hash(muscle_groups, equipment_types, limit, offset)
        cache_key = filtered_cache_key(filters_hash)
        serialized_exercises = json.dumps(exercises)
        await self._client.setex(cache_key, EXERCISE_LIST_TTL, serialized_exercises)


_redis_client = RedisClient()


async def get_redis_client() -> RedisClient:
    if not _redis_client.is_connected():
        await _redis_client.initialize()
    return _redis_client


async def init_redis() -> None:
    await _redis_client.initialize()


async def close_redis() -> None:
    await _redis_client.close()


@asynccontextmanager
async def redis_client_context() -> AsyncGenerator[RedisClient, None]:
    await _redis_client.initialize()
    try:
        yield _redis_client
    finally:
        await _redis_client.close()
