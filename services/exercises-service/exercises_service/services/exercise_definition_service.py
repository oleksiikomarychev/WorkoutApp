import asyncio
import functools

import msgpack
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
    def __init__(self, db: AsyncSession, redis_client: RedisClient | None = None):
        self.db = db
        self.redis_client = redis_client
        self.repository = ExerciseRepository()
        self.logger = structlog.get_logger(__name__)

    @property
    def _cache_available(self) -> bool:
        return bool(self.redis_client and self.redis_client.is_connected())

    def cache_metrics(func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            try:
                result = await func(self, *args, **kwargs)
                return result
            except Exception as e:
                EXERCISE_CACHE_ERRORS_TOTAL.inc()
                raise e
        return wrapper

    async def _get_from_cache(self, cache_key: str):
        if not self.redis_client or not self.redis_client.is_connected():
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
            return msgpack.loads(cached_value)
        except Exception:
            EXERCISE_CACHE_ERRORS_TOTAL.inc()
            return _CACHE_MISS

    async def _cache_operation(self, cache_key: str, data_func, ttl: int = 1800):
        if self.redis_client and self.redis_client.is_connected():
            cached = await self._get_from_cache(cache_key)
            if cached is not _CACHE_MISS:
                return cached
        
        data = await data_func()
        
        if self.redis_client and self.redis_client.is_connected() and data is not None:
            try:
                pipe = self.redis_client.client.pipeline()
                if isinstance(data, list):
                    cache_value = msgpack.dumps([item.model_dump(mode="json") if hasattr(item, 'model_dump') else item for item in data])
                else:
                    cache_value = msgpack.dumps(data.model_dump(mode="json") if hasattr(data, 'model_dump') else data)
                pipe.set(cache_key, cache_value, ex=ttl)
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
        search: str | None = None
    ):
        if ids is not None:
            if ids and len(ids) > 1000:
                ids_tuple = tuple(await asyncio.to_thread(sorted, ids))
            else:
                ids_tuple = tuple(sorted(ids)) if ids else None
            
            cache_key = exercise_definitions_list_key(ids_tuple)
            
            if self._cache_available and not muscle_groups and not equipment_types and not search:
                cached = await self._get_from_cache(cache_key)
                if cached is not _CACHE_MISS:
                    return cached
            
            definitions = await self.repository.list_exercise_definitions(
                self.db, ids, limit, offset, muscle_groups, equipment_types, search
            )
            responses = [schemas.ExerciseListResponse.model_validate(defn) for defn in definitions]
            
            if self._cache_available and not muscle_groups and not equipment_types and not search:
                try:
                    pipe = self.redis_client.client.pipeline()
                    pipe.set(cache_key, msgpack.dumps([item.model_dump(mode="json") for item in responses]), ex=1800)
                    await pipe.execute()
                except Exception:
                    self.logger.warning("Failed to set exercise definition cache", key=cache_key, exc_info=True)
            
            return responses
        
        if self._cache_available:
            cached_list = await self.redis_client.get_smart_exercise_list(muscle_groups, equipment_types, limit or 50, offset)
            if cached_list:
                EXERCISE_CACHE_HITS_TOTAL.inc()
                try:
                    cached_exercises = [schemas.ExerciseListResponse.model_validate(item) for item in cached_list]
                    return cached_exercises
                except Exception:
                    EXERCISE_CACHE_ERRORS_TOTAL.inc()
        
        EXERCISE_CACHE_MISSES_TOTAL.inc()
        definitions = await self.repository.list_exercise_definitions(
            self.db, ids, limit, offset, muscle_groups, equipment_types, search
        )
        responses = [schemas.ExerciseListResponse.model_validate(defn) for defn in definitions]
        
        if self.redis_client and self.redis_client.is_connected():
            try:
                await self.redis_client.set_smart_exercise_list(
                    [item.model_dump(mode="json") for item in responses],
                    muscle_groups, equipment_types, limit or 50, offset
                )
            except Exception:
                filters_hash = generate_filters_hash(muscle_groups, equipment_types, limit, offset)
                self.logger.warning("Failed to set smart cache", filters_hash=filters_hash, exc_info=True)
        
        return responses

    async def get_definition(self, exercise_list_id: int):
        
        if self._cache_available:
            cached_data = await self.redis_client.get_exercise_from_smart_cache(exercise_list_id)
            if cached_data:
                EXERCISE_CACHE_HITS_TOTAL.inc()
                try:
                    return msgpack.loads(cached_data)
                except Exception:
                    EXERCISE_CACHE_ERRORS_TOTAL.inc()
        
        EXERCISE_CACHE_MISSES_TOTAL.inc()
        definition = await self.repository.get_exercise_definition(self.db, exercise_list_id)
        
        if not definition:
            return None
        
        response = schemas.ExerciseListResponse.model_validate(definition)
        
        if self._cache_available:
            try:
                await self.redis_client.set_exercise_in_smart_cache(
                    exercise_list_id, 
                    response.model_dump(mode="json")
                )
            except Exception:
                self.logger.warning("Failed to set smart cache", id=exercise_list_id, exc_info=True)
        
        return response

    async def create_definition(self, exercise: schemas.ExerciseListCreate):
        try:
            existing = await self.repository.get_exercise_definition_by_name(self.db, exercise.name)
            if existing:
                return schemas.ExerciseListResponse.model_validate(existing)

            created = await self.repository.create_exercise_definition(self.db, exercise.model_dump())
            await self.db.commit()
            if self._cache_available:
                await self.redis_client.invalidate_exercise_cache()
            return schemas.ExerciseListResponse.model_validate(created)
        except Exception as e:
            await self.db.rollback()
            self.logger.error("Failed to create exercise definition", name=exercise.name, error=str(e), exc_info=True)
            raise e

    async def update_definition(self, exercise_list_id: int, exercise_update: schemas.ExerciseListCreate):
        try:
            updated = await self.repository.update_exercise_definition(
                self.db,
                exercise_list_id,
                exercise_update.model_dump(),
            )
            await self.db.commit()
            if self._cache_available:
                await self.redis_client.invalidate_exercise_cache(definition_ids=[exercise_list_id])
            return schemas.ExerciseListResponse.model_validate(updated)
        except Exception as e:
            await self.db.rollback()
            self.logger.error("Failed to update exercise definition", id=exercise_list_id, error=str(e), exc_info=True)
            raise e

    async def batch_upsert_definitions(self, exercises: list[schemas.ExerciseListCreate], batch_size: int = 1000):
        if not exercises:
            return []
        
        try:
            all_definition_ids = []
            
            for i in range(0, len(exercises), batch_size):
                batch = exercises[i:i + batch_size]
                payloads = [item.model_dump() for item in batch]
                result = await self.repository.batch_upsert_exercise_definitions(self.db, payloads)
                all_definition_ids.extend([item.id for item in result if item.id])
            
            await self.db.commit()
            
            if self._cache_available:
                affected_keys = []
                
                if all_definition_ids:
                    affected_keys.append(exercise_definitions_list_key(None))
                
                for def_id in all_definition_ids:
                    affected_keys.append(exercise_definition_key(def_id))
                
                await self.redis_client.invalidate_exercise_cache(
                    definition_ids=all_definition_ids,
                    specific_list_keys=affected_keys
                )
            
            if all_definition_ids:
                final_results = await self.repository.list_exercise_definitions(self.db, all_definition_ids)
                return [schemas.ExerciseListResponse.model_validate(item) for item in final_results]
            else:
                return []
                
        except Exception as e:
            await self.db.rollback()
            self.logger.error("Failed to batch upsert exercise definitions", error=str(e), exc_info=True)
            raise e

    async def delete_definition(self, exercise_list_id: int):
        try:
            result = await self.repository.delete_exercise_definition(self.db, exercise_list_id)
            await self.db.commit()
            if self._cache_available:
                await self.redis_client.invalidate_exercise_cache(definition_ids=[exercise_list_id])
            return result
        except Exception as e:
            await self.db.rollback()
            self.logger.error("Failed to delete exercise definition", id=exercise_list_id, error=str(e), exc_info=True)
            raise e
