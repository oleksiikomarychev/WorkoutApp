import json

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from .. import schemas
from ..metrics import (
    EXERCISE_CACHE_ERRORS_TOTAL,
    EXERCISE_CACHE_HITS_TOTAL,
    EXERCISE_CACHE_MISSES_TOTAL,
)
from ..redis_client import (
    EXERCISE_DEF_TTL_SECONDS,
    EXERCISE_LIST_TTL_SECONDS,
    exercise_definition_key,
    exercise_definitions_list_key,
    get_redis,
    invalidate_exercise_cache,
)
from ..repositories.exercise_repository import ExerciseRepository


class ExerciseDefinitionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = ExerciseRepository()
        self.logger = structlog.get_logger(__name__)

    async def list_definitions(self, ids: list[int] | None = None):
        ids_tuple = tuple(sorted(ids)) if ids else None
        cacheable = ids_tuple is None
        cache_key = exercise_definitions_list_key(ids_tuple)
        redis = await get_redis()

        if cacheable and redis:
            try:
                cached_value = await redis.get(cache_key)
                if cached_value:
                    EXERCISE_CACHE_HITS_TOTAL.inc()
                    raw_items = json.loads(cached_value)
                    return [schemas.ExerciseListResponse.model_validate(item) for item in raw_items]
                EXERCISE_CACHE_MISSES_TOTAL.inc()
            except Exception as exc:
                EXERCISE_CACHE_ERRORS_TOTAL.inc()
                self.logger.warning("exercise_cache_get_failed", key=cache_key, error=str(exc))

        definitions = await self.repository.list_exercise_definitions(self.db, ids)
        responses = [schemas.ExerciseListResponse.model_validate(defn) for defn in definitions]

        if cacheable and redis:
            try:
                payload = json.dumps([item.model_dump(mode="json") for item in responses])
                await redis.set(cache_key, payload, ex=EXERCISE_LIST_TTL_SECONDS)
            except Exception as exc:
                EXERCISE_CACHE_ERRORS_TOTAL.inc()
                self.logger.warning("exercise_cache_set_failed", key=cache_key, error=str(exc))

        return responses

    async def get_definition(self, exercise_list_id: int):
        cache_key = exercise_definition_key(exercise_list_id)
        redis = await get_redis()
        if redis:
            try:
                cached_value = await redis.get(cache_key)
                if cached_value:
                    EXERCISE_CACHE_HITS_TOTAL.inc()
                    return schemas.ExerciseListResponse.model_validate_json(cached_value)
                EXERCISE_CACHE_MISSES_TOTAL.inc()
            except Exception as exc:
                EXERCISE_CACHE_ERRORS_TOTAL.inc()
                self.logger.warning("exercise_cache_get_failed", key=cache_key, error=str(exc))

        definition = await self.repository.get_exercise_definition(self.db, exercise_list_id)
        if not definition:
            return None

        response = schemas.ExerciseListResponse.model_validate(definition)
        if redis:
            try:
                await redis.set(cache_key, response.model_dump_json(), ex=EXERCISE_DEF_TTL_SECONDS)
            except Exception as exc:
                EXERCISE_CACHE_ERRORS_TOTAL.inc()
                self.logger.warning("exercise_cache_set_failed", key=cache_key, error=str(exc))
        return response

    async def create_definition(self, exercise: schemas.ExerciseListCreate):
        created = await self.repository.create_exercise_definition(self.db, exercise.model_dump())
        await invalidate_exercise_cache()
        return schemas.ExerciseListResponse.model_validate(created)

    async def update_definition(self, exercise_list_id: int, exercise_update: schemas.ExerciseListCreate):
        updated = await self.repository.update_exercise_definition(
            self.db,
            exercise_list_id,
            exercise_update.model_dump(),
        )
        await invalidate_exercise_cache(definition_ids=[exercise_list_id])
        return schemas.ExerciseListResponse.model_validate(updated)

    async def delete_definition(self, exercise_list_id: int):
        result = await self.repository.delete_exercise_definition(self.db, exercise_list_id)
        await invalidate_exercise_cache(definition_ids=[exercise_list_id])
        return result
