import json
from typing import Any, List, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from .. import schemas
from ..metrics import (
    EXERCISE_CACHE_ERRORS_TOTAL,
    EXERCISE_CACHE_HITS_TOTAL,
    EXERCISE_CACHE_MISSES_TOTAL,
)
from ..redis_client import (
    EXERCISE_INSTANCE_TTL_SECONDS,
    EXERCISE_WORKOUT_TTL_SECONDS,
    exercise_instance_key,
    get_redis,
    invalidate_instance_cache,
    workout_instances_key,
)
from ..repositories.exercise_repository import ExerciseRepository
from .set_service import SetService

logger = structlog.get_logger(__name__)


class ExerciseInstanceService:
    def __init__(self, db: AsyncSession, set_service: SetService, user_id: str):
        self.db = db
        self.set_service = set_service
        self.repository = ExerciseRepository()
        self.user_id = user_id

    def _serialize_instance(self, instance: Any) -> dict:
        if instance is None:
            return {}
        if isinstance(instance, dict):
            normalized_sets = self.set_service.normalize_sets_for_frontend(instance.get("sets", []))
            return {**instance, "sets": normalized_sets}

        return {
            "id": instance.id,
            "exercise_list_id": instance.exercise_list_id,
            "sets": self.set_service.normalize_sets_for_frontend(instance.sets or []),
            "notes": instance.notes,
            "order": instance.order,
            "workout_id": instance.workout_id,
            "user_max_id": instance.user_max_id,
            "user_id": getattr(instance, "user_id", self.user_id),
        }

    async def _cache_instance(self, cache_key: str, payload: dict) -> None:
        redis = await get_redis()
        if not redis:
            return
        try:
            await redis.set(cache_key, json.dumps(payload), ex=EXERCISE_INSTANCE_TTL_SECONDS)
        except Exception as exc:
            EXERCISE_CACHE_ERRORS_TOTAL.inc()
            logger.warning("exercise_cache_set_failed", key=cache_key, error=str(exc))

    async def _cache_instances_list(self, cache_key: str, payload: List[dict]) -> None:
        redis = await get_redis()
        if not redis:
            return
        try:
            await redis.set(cache_key, json.dumps(payload), ex=EXERCISE_WORKOUT_TTL_SECONDS)
        except Exception as exc:
            EXERCISE_CACHE_ERRORS_TOTAL.inc()
            logger.warning("exercise_cache_set_failed", key=cache_key, error=str(exc))

    async def _get_cached_instance(self, cache_key: str) -> Optional[dict]:
        redis = await get_redis()
        if not redis:
            return None
        try:
            cached_value = await redis.get(cache_key)
            if cached_value:
                EXERCISE_CACHE_HITS_TOTAL.inc()
                return json.loads(cached_value)
            EXERCISE_CACHE_MISSES_TOTAL.inc()
        except Exception as exc:
            EXERCISE_CACHE_ERRORS_TOTAL.inc()
            logger.warning("exercise_cache_get_failed", key=cache_key, error=str(exc))
        return None

    async def _get_cached_instances_list(self, cache_key: str) -> Optional[List[dict]]:
        redis = await get_redis()
        if not redis:
            return None
        try:
            cached_value = await redis.get(cache_key)
            if cached_value:
                EXERCISE_CACHE_HITS_TOTAL.inc()
                return json.loads(cached_value)
            EXERCISE_CACHE_MISSES_TOTAL.inc()
        except Exception as exc:
            EXERCISE_CACHE_ERRORS_TOTAL.inc()
            logger.warning("exercise_cache_get_failed", key=cache_key, error=str(exc))
        return None

    async def get_instance(self, instance_id: int) -> Optional[dict]:
        cache_key = exercise_instance_key(self.user_id, instance_id)
        cached = await self._get_cached_instance(cache_key)
        if cached is not None:
            return cached

        db_instance = await self.repository.get_exercise_instance(self.db, instance_id, self.user_id)
        if not db_instance:
            return None
        serialized = self._serialize_instance(db_instance)
        await self._cache_instance(cache_key, serialized)
        return serialized

    async def get_instances_by_workout(self, workout_id: int) -> List[dict]:
        cache_key = workout_instances_key(self.user_id, workout_id)
        cached = await self._get_cached_instances_list(cache_key)
        if cached is not None:
            return cached

        db_instances = await self.repository.get_instances_by_workout(self.db, workout_id, self.user_id)
        if not db_instances:
            await self._cache_instances_list(cache_key, [])
            return []
        serialized = [self._serialize_instance(instance) for instance in db_instances]
        await self._cache_instances_list(cache_key, serialized)
        return serialized

    async def create_instance(self, workout_id: int, instance_data: schemas.ExerciseInstanceCreate) -> dict:
        logger.info(
            "exercise_instance_create_requested",
            workout_id=workout_id,
            user_id=self.user_id,
        )
        logger.debug("exercise_instance_payload", payload=instance_data.model_dump())

        # Проверяем существование определения упражнения
        logger.info("exercise_definition_lookup", exercise_definition_id=instance_data.exercise_list_id)
        definition = await ExerciseRepository.get_exercise_definition(self.db, instance_data.exercise_list_id)
        if not definition:
            logger.error(
                "exercise_definition_missing",
                exercise_definition_id=instance_data.exercise_list_id,
            )
            raise ValueError(f"Exercise definition with id {instance_data.exercise_list_id} not found")

        logger.debug("exercise_instance_prepare_data")
        instance_dict = instance_data.model_dump()
        instance_dict["workout_id"] = workout_id
        instance_dict["user_id"] = self.user_id
        if "sets" in instance_dict:
            instance_dict["sets"] = self.set_service.prepare_sets(instance_dict["sets"])
        logger.debug("exercise_instance_payload_prepared", payload=instance_dict)

        logger.info("exercise_instance_create_in_db", workout_id=workout_id)
        result = await self.repository.create_exercise_instance(self.db, instance_dict)
        logger.info("exercise_instance_create_success", instance_id=getattr(result, "id", None))

        serialized = self._serialize_instance(result)
        await invalidate_instance_cache(
            user_id=self.user_id,
            instance_ids=[serialized.get("id")],
            workout_ids=[workout_id],
        )
        await self._cache_instance(exercise_instance_key(self.user_id, serialized.get("id")), serialized)
        return serialized

    async def update_instance(self, instance_id: int, update_data: schemas.ExerciseInstanceBase) -> dict:
        db_instance = await self.repository.get_exercise_instance(self.db, instance_id, self.user_id)
        if not db_instance:
            raise ValueError("Exercise instance not found")
        update_dict = update_data.model_dump(exclude_unset=True)
        if "sets" in update_dict:
            update_dict["sets"] = self.set_service.prepare_sets(update_dict["sets"])
        updated_instance = await self.repository.update_exercise_instance(self.db, db_instance, update_dict)
        serialized = self._serialize_instance(updated_instance)
        await invalidate_instance_cache(
            user_id=self.user_id,
            instance_ids=[instance_id],
            workout_ids=[serialized.get("workout_id")],
        )
        return serialized

    async def update_set(self, instance_id: int, set_id: int, update_data: dict) -> dict:
        """
        Обновляет конкретный сет в экземпляре упражнения
        """
        db_instance = await self.repository.get_exercise_instance(self.db, instance_id, self.user_id)
        if not db_instance:
            raise ValueError("Exercise instance not found")
        if not isinstance(db_instance.sets, list):
            raise ValueError("No sets to update")

        # Синхронизация полей усилия: если приходит только одно из полей, зеркалим во второе
        try:
            if "rpe" in update_data and "effort" not in update_data:
                update_data["effort"] = update_data.get("rpe")
            if "effort" in update_data and "rpe" not in update_data:
                update_data["rpe"] = update_data.get("effort")
        except Exception:
            # best-effort only
            pass

        # Обновляем сет
        new_sets = self.set_service.update_set(db_instance.sets, set_id, update_data)

        # Обновляем экземпляр упражнения
        updated_instance = await self.repository.update_exercise_instance(self.db, db_instance, {"sets": new_sets})
        serialized = self._serialize_instance(updated_instance)
        await invalidate_instance_cache(
            user_id=self.user_id,
            instance_ids=[instance_id],
            workout_ids=[serialized.get("workout_id")],
        )
        return serialized

    async def delete_set(self, instance_id: int, set_id: int) -> None:
        db_instance = await self.repository.get_exercise_instance(self.db, instance_id, self.user_id)
        if not db_instance:
            raise ValueError("Exercise instance not found")
        if not isinstance(db_instance.sets, list):
            raise ValueError("No sets to delete")
        new_sets = [s for s in db_instance.sets if not (isinstance(s, dict) and s.get("id") == set_id)]
        if len(new_sets) == len(db_instance.sets):
            raise ValueError("Set not found")
        await self.repository.update_exercise_instance(self.db, db_instance, {"sets": new_sets})
        await invalidate_instance_cache(
            user_id=self.user_id,
            instance_ids=[instance_id],
            workout_ids=[db_instance.workout_id],
        )

    async def delete_instance(self, instance_id: int) -> None:
        db_instance = await self.repository.get_exercise_instance(self.db, instance_id, self.user_id)
        workout_id = getattr(db_instance, "workout_id", None)
        await self.repository.delete_exercise_instance(self.db, instance_id, self.user_id)
        await invalidate_instance_cache(
            user_id=self.user_id,
            instance_ids=[instance_id],
            workout_ids=[workout_id],
        )
