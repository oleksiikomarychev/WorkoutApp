from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Coroutine
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from .. import schemas
from ..metrics import (
    EXERCISE_CACHE_ERRORS_TOTAL,
    EXERCISE_CACHE_HITS_TOTAL,
    EXERCISE_CACHE_MISSES_TOTAL,
)
from ..redis_client import (
    RedisClient,
    exercise_definition_key,
    exercise_definitions_list_key,
    generate_filters_hash,
)
from ..repositories.exercise_repository import ExerciseRepository

_CACHE_MISS = object()


class ExerciseDefinitionService:
    """Business logic service for managing exercise definitions and cache."""

    def __init__(self, db: AsyncSession, redis_client: RedisClient | None = None) -> None:
        self.db = db
        self.redis_client = redis_client
        self.repository = ExerciseRepository()
        self.logger = structlog.get_logger(__name__)

    @property
    def _cache_available(self) -> bool:
        return bool(self.redis_client and self.redis_client.is_connected())

    async def _get_from_cache(self, cache_key: str) -> Any:
        """Fetch and deserialise a cached JSON item from Redis."""
        if not self.redis_client or not self.redis_client.is_connected() or self.redis_client.client is None:
            EXERCISE_CACHE_ERRORS_TOTAL.inc()
            return _CACHE_MISS

        try:
            cached_value = await self.redis_client.client.get(cache_key)
        except Exception:
            EXERCISE_CACHE_ERRORS_TOTAL.inc()
            return _CACHE_MISS

        if cached_value is None:
            EXERCISE_CACHE_MISSES_TOTAL.inc()
            return _CACHE_MISS

        EXERCISE_CACHE_HITS_TOTAL.inc()
        if cached_value == "__NULL__":
            return None

        try:
            if isinstance(cached_value, (bytes, bytearray)):
                return json.loads(cached_value.decode("utf-8"))
            return json.loads(cached_value)
        except Exception:
            EXERCISE_CACHE_ERRORS_TOTAL.inc()
            return _CACHE_MISS

    async def _cache_operation(
        self,
        cache_key: str,
        data_func: Callable[[], Coroutine[Any, Any, Any]],
        ttl: int = 1800,
    ) -> Any:
        """Execute operation with cache lookaside strategy."""
        if self._cache_available:
            cached = await self._get_from_cache(cache_key)
            if cached is not _CACHE_MISS:
                return cached

        data = await data_func()

        if self._cache_available and self.redis_client and self.redis_client.client is not None and data is not None:
            try:
                pipe = self.redis_client.client.pipeline()
                if isinstance(data, list):
                    dumped = [item.model_dump(mode="json") if hasattr(item, "model_dump") else item for item in data]
                else:
                    dumped = data.model_dump(mode="json") if hasattr(data, "model_dump") else data

                pipe.set(cache_key, json.dumps(dumped), ex=ttl)
                await pipe.execute()
            except Exception:
                self.logger.warning("Failed to set cache", key=cache_key, exc_info=True)

        return data

    async def list_definitions(
        self,
        ids: list[int] | None = None,
        limit: int | None = None,
        offset: int = 0,
        muscle_groups: list[str] | None = None,
        equipment_types: list[str] | None = None,
        search: str | None = None,
    ) -> list[schemas.ExerciseListResponse]:
        """List exercise definitions with Redis caching for repeated queries."""
        if ids is not None:
            if ids and len(ids) > 1000:
                ids_tuple = tuple(await asyncio.to_thread(sorted, ids))
            else:
                ids_tuple = tuple(sorted(ids)) if ids else None

            cache_key = exercise_definitions_list_key(ids_tuple)

            if self._cache_available and not muscle_groups and not equipment_types and not search:
                cached = await self._get_from_cache(cache_key)
                if cached is not _CACHE_MISS and isinstance(cached, list):
                    return [schemas.ExerciseListResponse.model_validate(item) for item in cached]

            definitions = await self.repository.list_exercise_definitions(
                self.db, ids, limit, offset, muscle_groups, equipment_types, search
            )
            responses = [schemas.ExerciseListResponse.model_validate(defn) for defn in definitions]

            if (
                self._cache_available
                and self.redis_client
                and self.redis_client.client is not None
                and not muscle_groups
                and not equipment_types
                and not search
            ):
                try:
                    pipe = self.redis_client.client.pipeline()
                    serialized_list = json.dumps([item.model_dump(mode="json") for item in responses])
                    pipe.set(cache_key, serialized_list, ex=1800)
                    await pipe.execute()
                except Exception:
                    self.logger.warning("Failed to set exercise definition cache", key=cache_key, exc_info=True)

            return responses

        # Query without explicit ID list
        if self._cache_available and self.redis_client is not None:
            cached_list = await self.redis_client.get_smart_exercise_list(
                muscle_groups, equipment_types, limit or 50, offset
            )
            if cached_list:
                EXERCISE_CACHE_HITS_TOTAL.inc()
                try:
                    return [schemas.ExerciseListResponse.model_validate(item) for item in cached_list]
                except Exception:
                    EXERCISE_CACHE_ERRORS_TOTAL.inc()

        EXERCISE_CACHE_MISSES_TOTAL.inc()
        definitions = await self.repository.list_exercise_definitions(
            self.db, ids, limit, offset, muscle_groups, equipment_types, search
        )
        responses = [schemas.ExerciseListResponse.model_validate(defn) for defn in definitions]

        if self._cache_available and self.redis_client is not None:
            try:
                await self.redis_client.set_smart_exercise_list(
                    [item.model_dump(mode="json") for item in responses],
                    muscle_groups,
                    equipment_types,
                    limit or 50,
                    offset,
                )
            except Exception:
                filters_hash = generate_filters_hash(muscle_groups, equipment_types, limit, offset)
                self.logger.warning("Failed to set smart cache", filters_hash=filters_hash, exc_info=True)

        return responses

    async def get_definition(self, exercise_list_id: int) -> schemas.ExerciseListResponse | None:
        """Get a single exercise definition by ID with cache lookup."""
        if self._cache_available and self.redis_client is not None:
            cached_data = await self.redis_client.get_exercise_from_smart_cache(exercise_list_id)
            if cached_data:
                EXERCISE_CACHE_HITS_TOTAL.inc()
                try:
                    return schemas.ExerciseListResponse.model_validate(cached_data)
                except Exception:
                    EXERCISE_CACHE_ERRORS_TOTAL.inc()

        EXERCISE_CACHE_MISSES_TOTAL.inc()
        definition = await self.repository.get_exercise_definition(self.db, exercise_list_id)

        if not definition:
            return None

        response = schemas.ExerciseListResponse.model_validate(definition)

        if self._cache_available and self.redis_client is not None:
            try:
                await self.redis_client.set_exercise_in_smart_cache(
                    exercise_list_id,
                    response.model_dump(mode="json"),
                )
            except Exception:
                self.logger.warning("Failed to set smart cache", id=exercise_list_id, exc_info=True)

        return response

    async def create_definition(self, exercise: schemas.ExerciseListCreate) -> schemas.ExerciseListResponse:
        """Create an exercise definition if not already present by name."""
        try:
            existing = await self.repository.get_exercise_definition_by_name(self.db, exercise.name)
            if existing:
                return schemas.ExerciseListResponse.model_validate(existing)

            created = await self.repository.create_exercise_definition(self.db, exercise.model_dump())
            await self.db.commit()
            if self._cache_available and self.redis_client is not None:
                await self.redis_client.invalidate_exercise_cache()
            return schemas.ExerciseListResponse.model_validate(created)
        except Exception as e:
            await self.db.rollback()
            self.logger.error("Failed to create exercise definition", name=exercise.name, error=str(e), exc_info=True)
            raise

    async def update_definition(
        self, exercise_list_id: int, exercise_update: schemas.ExerciseListCreate
    ) -> schemas.ExerciseListResponse:
        """Update an existing exercise definition and invalidate its cache."""
        try:
            updated = await self.repository.update_exercise_definition(
                self.db,
                exercise_list_id,
                exercise_update.model_dump(),
            )
            await self.db.commit()
            if self._cache_available and self.redis_client is not None:
                await self.redis_client.invalidate_exercise_cache(definition_ids=[exercise_list_id])
            return schemas.ExerciseListResponse.model_validate(updated)
        except Exception as e:
            await self.db.rollback()
            self.logger.error("Failed to update exercise definition", id=exercise_list_id, error=str(e), exc_info=True)
            raise

    async def batch_upsert_definitions(
        self, exercises: list[schemas.ExerciseListCreate], batch_size: int = 1000
    ) -> list[schemas.ExerciseListResponse]:
        """Batch upsert multiple exercise definitions and invalidate affected cache keys."""
        if not exercises:
            return []

        try:
            all_definition_ids: list[int] = []

            for i in range(0, len(exercises), batch_size):
                batch = exercises[i : i + batch_size]
                payloads = [item.model_dump() for item in batch]
                result = await self.repository.batch_upsert_exercise_definitions(self.db, payloads)
                all_definition_ids.extend([item.id for item in result if item.id])

            await self.db.commit()

            if self._cache_available and self.redis_client is not None:
                affected_keys: list[str] = []

                if all_definition_ids:
                    affected_keys.append(exercise_definitions_list_key(None))

                for def_id in all_definition_ids:
                    affected_keys.append(exercise_definition_key(def_id))

                await self.redis_client.invalidate_exercise_cache(
                    definition_ids=all_definition_ids,
                    specific_list_keys=affected_keys,
                )

            if all_definition_ids:
                final_results = await self.repository.list_exercise_definitions(self.db, all_definition_ids)
                return [schemas.ExerciseListResponse.model_validate(item) for item in final_results]
            return []

        except Exception as e:
            await self.db.rollback()
            self.logger.error("Failed to batch upsert exercise definitions", error=str(e), exc_info=True)
            raise

    async def delete_definition(self, exercise_list_id: int) -> bool:
        """Delete an exercise definition and invalidate cache."""
        try:
            result = await self.repository.delete_exercise_definition(self.db, exercise_list_id)
            await self.db.commit()
            if self._cache_available and self.redis_client is not None:
                await self.redis_client.invalidate_exercise_cache(definition_ids=[exercise_list_id])
            return result
        except Exception as e:
            await self.db.rollback()
            self.logger.error("Failed to delete exercise definition", id=exercise_list_id, error=str(e), exc_info=True)
            raise
