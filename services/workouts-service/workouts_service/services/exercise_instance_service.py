from typing import Any

import structlog
from backend_common.cache import CacheHelper, CacheMetrics
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .. import models
from ..metrics import WORKOUT_CACHE_ERRORS_TOTAL, WORKOUT_CACHE_HITS_TOTAL, WORKOUT_CACHE_MISSES_TOTAL
from ..redis_client import get_redis, invalidate_workout_cache
from ..schemas import workout as workout_schemas

logger = structlog.get_logger(__name__)

WORKOUT_EXERCISE_TTL_SECONDS = 10 * 60
WORKOUT_EXERCISES_BY_WORKOUT_TTL_SECONDS = 5 * 60


def workout_exercise_key(user_id: str, workout_exercise_id: int) -> str:
    return f"workouts:exercise:{user_id}:{workout_exercise_id}"


def workout_exercises_by_workout_key(user_id: str, workout_id: int) -> str:
    return f"workouts:exercise:list:{user_id}:{workout_id}"


class ExerciseInstanceService:
    def __init__(self, db: AsyncSession, user_id: str):
        self.db = db
        self.user_id = user_id
        self._cache = CacheHelper(
            get_redis=get_redis,
            metrics=CacheMetrics(
                hits=WORKOUT_CACHE_HITS_TOTAL,
                misses=WORKOUT_CACHE_MISSES_TOTAL,
                errors=WORKOUT_CACHE_ERRORS_TOTAL,
            ),
            default_ttl=WORKOUT_EXERCISE_TTL_SECONDS,
        )

    def _serialize_instance(self, instance: Any) -> dict:
        if instance is None:
            return {}
        if isinstance(instance, dict):
            return dict(instance)

        sets_payload: list[dict] = []
        raw_sets = getattr(instance, "sets", None) or []
        for s in raw_sets:
            sets_payload.append(
                {
                    "id": getattr(s, "id", None),
                    "order_index": getattr(s, "order_index", None),
                    "intensity": getattr(s, "intensity", None),
                    "effort": getattr(s, "effort", None),
                    "volume": getattr(s, "volume", None),
                    "working_weight": getattr(s, "working_weight", None),
                    "set_type": getattr(s, "set_type", None),
                    "subsets": getattr(s, "subsets", None),
                }
            )

        return {
            "id": instance.id,
            "exercise_list_id": instance.exercise_id,
            "order": getattr(instance, "order", None),
            "notes": getattr(instance, "notes", None),
            "rest_seconds": getattr(instance, "rest_seconds", None),
            "sets": sets_payload,
        }

    async def _cache_instance(self, cache_key: str, payload: dict) -> None:
        await self._cache.set(cache_key, payload)

    async def _cache_instances_list(self, cache_key: str, payload: list[dict]) -> None:
        await self._cache.set(cache_key, payload, ttl=WORKOUT_EXERCISES_BY_WORKOUT_TTL_SECONDS)

    async def _get_cached_instance(self, cache_key: str) -> dict | None:
        return await self._cache.get(cache_key)

    async def _get_cached_instances_list(self, cache_key: str) -> list[dict] | None:
        return await self._cache.get(cache_key)

    async def get_instance(self, instance_id: int) -> dict | None:
        cache_key = workout_exercise_key(self.user_id, instance_id)
        cached = await self._get_cached_instance(cache_key)
        if cached is not None:
            return cached

        stmt = (
            select(models.WorkoutExercise)
            .options(selectinload(models.WorkoutExercise.sets))
            .where(
                models.WorkoutExercise.id == instance_id,
                models.WorkoutExercise.user_id == self.user_id,
            )
        )
        res = await self.db.execute(stmt)
        db_instance = res.scalars().first()
        if db_instance is None:
            return None

        serialized = self._serialize_instance(db_instance)
        await self._cache_instance(cache_key, serialized)
        return serialized

    async def get_instances_by_workout(self, workout_id: int) -> list[dict]:
        cache_key = workout_exercises_by_workout_key(self.user_id, workout_id)
        cached = await self._get_cached_instances_list(cache_key)
        if cached is not None:
            return cached

        stmt = (
            select(models.WorkoutExercise)
            .options(selectinload(models.WorkoutExercise.sets))
            .where(
                models.WorkoutExercise.workout_id == workout_id,
                models.WorkoutExercise.user_id == self.user_id,
            )
            .order_by(models.WorkoutExercise.order.asc().nulls_last(), models.WorkoutExercise.id.asc())
        )
        res = await self.db.execute(stmt)
        db_instances = res.scalars().all()
        if not db_instances:
            await self._cache_instances_list(cache_key, [])
            return []

        serialized = [self._serialize_instance(instance) for instance in db_instances]
        await self._cache_instances_list(cache_key, serialized)
        return serialized

    async def _invalidate_local_cache(self, *, workout_id: int | None = None, instance_id: int | None = None) -> None:
        redis = await get_redis()
        if redis is None:
            return
        keys: list[str] = []
        if instance_id is not None:
            keys.append(workout_exercise_key(self.user_id, int(instance_id)))
        if workout_id is not None:
            keys.append(workout_exercises_by_workout_key(self.user_id, int(workout_id)))
        if keys:
            try:
                await redis.delete(*keys)
            except Exception:
                logger.warning("workout_exercise_cache_invalidate_failed", keys=keys, exc_info=True)

    async def create_instance(self, workout_id: int, instance_data: workout_schemas.WorkoutExerciseInstanceCreate) -> dict:
        logger.info(
            "exercise_instance_create_requested",
            workout_id=workout_id,
            user_id=self.user_id,
        )
        if logger.isEnabledFor(10):
            logger.debug("exercise_instance_payload", payload=instance_data.model_dump())

        ex = models.WorkoutExercise(
            user_id=self.user_id,
            workout_id=workout_id,
            exercise_id=int(instance_data.exercise_id),
            order=instance_data.order,
            notes=instance_data.notes,
            rest_seconds=instance_data.rest_seconds,
        )
        self.db.add(ex)
        await self.db.flush()

        for idx, s in enumerate(instance_data.sets or []):
            ws = models.WorkoutSet(
                exercise_id=ex.id,
                order_index=s.order_index if s.order_index is not None else idx,
                intensity=s.intensity,
                effort=s.effort,
                volume=s.volume,
                working_weight=s.working_weight,
                set_type=s.set_type,
                subsets=s.subsets,
            )
            self.db.add(ws)

        await self.db.commit()
        await self.db.refresh(ex)

        stmt = select(models.WorkoutExercise).options(selectinload(models.WorkoutExercise.sets)).where(
            models.WorkoutExercise.id == ex.id
        )
        res = await self.db.execute(stmt)
        ex_full = res.scalars().first() or ex

        serialized = self._serialize_instance(ex_full)
        await self._invalidate_local_cache(workout_id=workout_id, instance_id=ex.id)
        await invalidate_workout_cache(self.user_id, workout_ids=[workout_id])
        await self._cache_instance(workout_exercise_key(self.user_id, ex.id), serialized)
        return serialized

    async def update_instance(self, instance_id: int, update_data: workout_schemas.WorkoutExerciseInstanceUpdate) -> dict:
        stmt = select(models.WorkoutExercise).where(
            models.WorkoutExercise.id == instance_id,
            models.WorkoutExercise.user_id == self.user_id,
        )
        res = await self.db.execute(stmt)
        db_instance = res.scalars().first()
        if db_instance is None:
            raise ValueError("Exercise instance not found")

        update_dict = update_data.model_dump(exclude_unset=True)
        if "exercise_id" in update_dict:
            db_instance.exercise_id = int(update_dict["exercise_id"])
        if "order" in update_dict:
            db_instance.order = update_dict.get("order")
        if "notes" in update_dict:
            db_instance.notes = update_dict.get("notes")
        if "rest_seconds" in update_dict:
            db_instance.rest_seconds = update_dict.get("rest_seconds")

        await self.db.commit()

        stmt = select(models.WorkoutExercise).options(selectinload(models.WorkoutExercise.sets)).where(
            models.WorkoutExercise.id == instance_id
        )
        res = await self.db.execute(stmt)
        updated_full = res.scalars().first()
        serialized = self._serialize_instance(updated_full)

        await self._invalidate_local_cache(workout_id=getattr(db_instance, "workout_id", None), instance_id=instance_id)
        await invalidate_workout_cache(self.user_id, workout_ids=[db_instance.workout_id])
        await self._cache_instance(workout_exercise_key(self.user_id, instance_id), serialized)
        return serialized

    async def update_set(self, instance_id: int, set_id: int, update_data: dict) -> dict:
        stmt = (
            select(models.WorkoutSet, models.WorkoutExercise.workout_id)
            .join(models.WorkoutExercise, models.WorkoutSet.exercise_id == models.WorkoutExercise.id)
            .where(
                models.WorkoutSet.id == set_id,
                models.WorkoutExercise.id == instance_id,
                models.WorkoutExercise.user_id == self.user_id,
            )
        )
        res = await self.db.execute(stmt)
        row = res.first()
        if row is None:
            raise ValueError("Set not found")

        db_set, workout_id = row

        if "order_index" in update_data:
            db_set.order_index = update_data.get("order_index")
        if "intensity" in update_data:
            db_set.intensity = update_data.get("intensity")
        if "effort" in update_data:
            db_set.effort = update_data.get("effort")
        if "volume" in update_data:
            db_set.volume = update_data.get("volume")
        if "working_weight" in update_data:
            db_set.working_weight = update_data.get("working_weight")
        if "set_type" in update_data:
            db_set.set_type = update_data.get("set_type")
        if "subsets" in update_data:
            db_set.subsets = update_data.get("subsets")

        await self.db.commit()

        refreshed = await self.get_instance(instance_id)
        await self._invalidate_local_cache(workout_id=workout_id, instance_id=instance_id)
        await invalidate_workout_cache(self.user_id, workout_ids=[workout_id])
        if refreshed is not None:
            await self._cache_instance(workout_exercise_key(self.user_id, instance_id), refreshed)
            return refreshed
        return {}

    async def delete_set(self, instance_id: int, set_id: int) -> None:
        stmt = (
            select(models.WorkoutSet, models.WorkoutExercise.workout_id)
            .join(models.WorkoutExercise, models.WorkoutSet.exercise_id == models.WorkoutExercise.id)
            .where(
                models.WorkoutSet.id == set_id,
                models.WorkoutExercise.id == instance_id,
                models.WorkoutExercise.user_id == self.user_id,
            )
        )
        res = await self.db.execute(stmt)
        row = res.first()
        if row is None:
            raise ValueError("Set not found")

        db_set, workout_id = row
        await self.db.delete(db_set)
        await self.db.commit()

        await self._invalidate_local_cache(workout_id=workout_id, instance_id=instance_id)
        await invalidate_workout_cache(self.user_id, workout_ids=[workout_id])

    async def delete_instance(self, instance_id: int) -> None:
        stmt = select(models.WorkoutExercise).where(
            models.WorkoutExercise.id == instance_id,
            models.WorkoutExercise.user_id == self.user_id,
        )
        res = await self.db.execute(stmt)
        db_instance = res.scalars().first()
        if db_instance is None:
            return

        workout_id = db_instance.workout_id
        await self.db.delete(db_instance)
        await self.db.commit()

        await self._invalidate_local_cache(workout_id=workout_id, instance_id=instance_id)
        await invalidate_workout_cache(self.user_id, workout_ids=[workout_id])
