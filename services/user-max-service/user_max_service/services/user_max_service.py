import hashlib
import logging
import time
from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..models import UserMax
from ..repositories import UserMaxRepository
from .analysis_service import aggregate_exercise_strength_from_daily_agg, compute_weak_muscles
from .exercise_service import get_all_exercises_meta, get_exercise_name_by_id_async
from .true_1rm_service import calculate_true_1rm

logger = logging.getLogger(__name__)


def _mask_uid(uid: str) -> str:
    digest = hashlib.sha256((uid or "").encode("utf-8")).hexdigest()[:12]
    return f"uid:{digest}"


class UserMaxService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UserMaxRepository(db)
        self._exercise_cache: dict[int, str] = {}
        self._cache_timestamp: float = 0
        self._cache_ttl = 3600
        self._cache_max_size = 1000
        self._all_exercises_cache: list[dict] = []
        self._all_exercises_cache_timestamp: float = 0  # 1 час

    async def _get_exercise_name_cached_async(self, exercise_id: int) -> str:
        if exercise_id in self._exercise_cache:
            return self._exercise_cache[exercise_id]
        
        try:
            name = await get_exercise_name_by_id_async(exercise_id)
            self._exercise_cache[exercise_id] = name
            return name
        except HTTPException as e:
            if e.status_code == 503:
                logger.error(f"Exercises-service unavailable for ID {exercise_id}: {e.detail}")
                self._exercise_cache[exercise_id] = "Unknown"
                return "Unknown"
            else:
                raise
        except Exception as e:
            logger.error(f"Unexpected error fetching exercise name for ID {exercise_id}: {str(e)}")
            self._exercise_cache[exercise_id] = "Unknown"
            return "Unknown"

    def _get_exercise_name_cached(self, exercise_id: int) -> str:
        if self._cache_timestamp + self._cache_ttl > time.time() and exercise_id in self._exercise_cache:
            return self._exercise_cache[exercise_id]
        
        if len(self._exercise_cache) >= self._cache_max_size:
            self._exercise_cache.clear()
        
        try:
            name = get_exercise_name_by_id(exercise_id)
            self._exercise_cache[exercise_id] = name
            self._cache_timestamp = time.time()
            return name
        except HTTPException as e:
            if e.status_code == 503:
                logger.error(f"Exercises-service unavailable for ID {exercise_id}: {e.detail}")
                self._exercise_cache[exercise_id] = "Unknown"
                return "Unknown"
            else:
                raise
        except Exception as e:
            logger.error(f"Unexpected error fetching exercise name for ID {exercise_id}: {str(e)}")
            self._exercise_cache[exercise_id] = "Unknown"
            return "Unknown"

    def _get_exercise_names_batch_sync(self, exercise_ids: list[int]) -> dict[int, str]:
        if not exercise_ids:
            return {}
        
        exercise_names: dict[int, str] = {}
        current_time = time.time()
        
        if self._all_exercises_cache_timestamp + self._cache_ttl > current_time:
            all_exercises = self._all_exercises_cache
        else:
            try:
                all_exercises = get_all_exercises_meta()
                self._all_exercises_cache = all_exercises
                self._all_exercises_cache_timestamp = current_time
            except Exception as e:
                logger.error(f"Failed to load exercise names batch: {str(e)}")
                for exercise_id in exercise_ids:
                    exercise_names[exercise_id] = "Unknown"
                    self._exercise_cache[exercise_id] = "Unknown"
                return exercise_names
        
        exercise_map = {ex.get("id"): ex.get("name", "Unknown") for ex in all_exercises if ex.get("id")}
        
        for exercise_id in exercise_ids:
            if exercise_id in exercise_map:
                exercise_names[exercise_id] = exercise_map[exercise_id]
                self._exercise_cache[exercise_id] = exercise_map[exercise_id]
            else:
                exercise_names[exercise_id] = "Unknown"
                self._exercise_cache[exercise_id] = "Unknown"
        
        return exercise_names

    def _recompute_daily_agg_for(self, user_id: str, exercise_id: int, dt: date) -> None:
        rows = self.repo.get_user_maxes_for_recompute(user_id, exercise_id, dt)
        
        if not rows:
            self.repo.delete_daily_agg_record(user_id, exercise_id, dt)
            return

        sum_true_1rm = 0.0
        cnt = 0
        for um in rows:
            val = um.verified_1rm if getattr(um, "verified_1rm", None) is not None else calculate_true_1rm(um)
            try:
                v = float(val)
            except (TypeError, ValueError):
                continue
            sum_true_1rm += v
            cnt += 1

        if cnt > 0:
            self.repo.create_or_update_daily_agg(user_id, exercise_id, dt, sum_true_1rm, cnt)

    def get_user_max_or_404(self, user_max_id: int, user_id: str) -> UserMax:
        user_max = self.repo.get_user_max_by_id(user_max_id, user_id)
        if user_max is None:
            raise HTTPException(status_code=404, detail=f"UserMax с id {user_max_id} не найден")
        return user_max

    def create_user_max(self, user_max: schemas.UserMaxCreate, user_id: str) -> UserMax:
        exercise_name = self._get_exercise_name_cached(user_max.exercise_id)

        existing = self.repo.find_existing_user_max(
            user_id, user_max.exercise_id, user_max.rep_max, user_max.date
        )
        
        if existing:
            if user_max.max_weight is not None:
                try:
                    if float(user_max.max_weight) > float(existing.max_weight or 0):
                        existing.max_weight = user_max.max_weight
                except (TypeError, ValueError):
                    pass
            
            if exercise_name and existing.exercise_name != exercise_name:
                existing.exercise_name = exercise_name

            for field in ['true_1rm', 'verified_1rm', 'source']:
                value = getattr(user_max, field, None)
                if value is not None:
                    setattr(existing, field, value)

            self._recompute_daily_agg_for(user_id, existing.exercise_id, existing.date)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        user_max_data = {
            "user_id": user_id,
            "exercise_id": user_max.exercise_id,
            "exercise_name": exercise_name,
            "max_weight": user_max.max_weight,
            "rep_max": user_max.rep_max,
            "date": user_max.date,
            "true_1rm": user_max.true_1rm,
            "verified_1rm": user_max.verified_1rm,
            "source": user_max.source,
        }
        
        db_user_max = self.repo.create_user_max(user_max_data)
        self._recompute_daily_agg_for(user_id, db_user_max.exercise_id, db_user_max.date)
        self.db.commit()
        self.db.refresh(db_user_max)
        return db_user_max

    def list_user_maxes(
        self, 
        user_id: str, 
        exercise_id: int | None = None, 
        skip: int = 0, 
        limit: int = 100
    ) -> list[UserMax]:
        user_maxes = self.repo.get_user_maxes_by_user(user_id, exercise_id, skip, limit)
        
        # Refresh exercise names for records that have "Unknown"
        exercise_ids_to_refresh = {um.exercise_id for um in user_maxes if um.exercise_name == "Unknown"}
        if exercise_ids_to_refresh:
            exercise_names = self._get_exercise_names_batch_sync(list(exercise_ids_to_refresh))
            updated = False
            for um in user_maxes:
                if um.exercise_name == "Unknown":
                    new_name = exercise_names.get(um.exercise_id, "Unknown")
                    if new_name != "Unknown":
                        um.exercise_name = new_name
                        self.repo.update_user_max(um, {"exercise_name": new_name})
                        updated = True
            if updated:
                self.db.commit()
                # Refresh the updated objects
                for um in user_maxes:
                    self.db.refresh(um)
        
        return user_maxes

    def get_by_exercise(
        self, 
        user_id: str, 
        exercise_id: int, 
        skip: int = 0, 
        limit: int = 100
    ) -> list[UserMax]:
        return self.repo.get_user_maxes_by_exercise(user_id, exercise_id, skip, limit)

    def get_user_maxes_by_exercises(self, user_id: str, exercise_ids: list[int]) -> list[UserMax]:
        if not all(isinstance(id, int) for id in exercise_ids):
            raise HTTPException(400, "Некорректные ID упражнений")
        return self.repo.get_user_maxes_by_exercises(user_id, exercise_ids)

    def get_user_maxes_by_ids(self, user_id: str, ids: list[int]) -> list[UserMax]:
        if not ids:
            raise HTTPException(status_code=400, detail="Необходимо указать хотя бы один идентификатор user_max")
        invalid = [value for value in ids if not isinstance(value, int)]
        if invalid:
            raise HTTPException(status_code=400, detail="Список идентификаторов содержит некорректные значения")
        return self.repo.get_user_maxes_by_ids(user_id, ids)

    def update_user_max(self, user_max: UserMax, payload: schemas.UserMaxUpdate) -> UserMax:
        if "date" in payload.model_dump():
            raise HTTPException(status_code=400, detail="date field is not allowed to update")
        
        old_exercise_id = user_max.exercise_id
        old_date = user_max.date
        
        self.repo.update_user_max(user_max, payload.model_dump())
        
        self._recompute_daily_agg_for(user_max.user_id, old_exercise_id, old_date)
        if user_max.exercise_id != old_exercise_id or user_max.date != old_date:
            self._recompute_daily_agg_for(user_max.user_id, user_max.exercise_id, user_max.date)
        
        self.db.commit()
        self.db.refresh(user_max)
        return user_max

    def delete_user_max(self, user_max: UserMax) -> None:
        user_id = user_max.user_id
        exercise_id = user_max.exercise_id
        dt = user_max.date
        
        self.repo.delete_user_max(user_max)
        self._recompute_daily_agg_for(user_id, exercise_id, dt)
        self.db.commit()

    def calculate_true_1rm(self, user_max: UserMax) -> float:
        return calculate_true_1rm(user_max)

    def verify_1rm(self, user_max: UserMax, verified_1rm: float) -> UserMax:
        user_max.verified_1rm = verified_1rm
        self.db.commit()
        self.db.refresh(user_max)
        return user_max


    def bulk_create_user_max(self, user_maxes: list[schemas.UserMaxCreate], user_id: str) -> list[UserMax]:
        logger.info(f"Received bulk create request with {len(user_maxes)} items for user {_mask_uid(user_id)}")

        exercise_ids = list({um.exercise_id for um in user_maxes})
        exercise_names = self._get_exercise_names_batch_sync(exercise_ids)

        merged: dict[tuple, schemas.UserMaxCreate] = {}
        for um in user_maxes:
            key = (um.exercise_id, um.rep_max, um.date)
            existing = merged.get(key)
            if not existing or um.max_weight > existing.max_weight:
                merged[key] = um

        exercise_id_date_pairs = [(um.exercise_id, um.date) for um in merged.values()]
        existing_records = self.repo.find_existing_user_max_bulk(user_id, exercise_id_date_pairs) if exercise_id_date_pairs else {}
        
        to_update: list[UserMax] = []
        to_create: list[dict] = []
        touched_pairs: set[tuple[int, date]] = set()
        
        for (exercise_id, rep_max, dt), um in merged.items():
            key = (exercise_id, rep_max, dt)
            existing = existing_records.get(key)
            
            if existing:
                if um.max_weight is not None:
                    try:
                        if float(um.max_weight) > float(existing.max_weight or 0):
                            existing.max_weight = um.max_weight
                    except (TypeError, ValueError):
                        pass
                
                ex_name = exercise_names.get(exercise_id, "Unknown")
                if ex_name and existing.exercise_name != ex_name:
                    existing.exercise_name = ex_name
                
                fields_to_update = ['true_1rm', 'verified_1rm', 'source']
                for field in fields_to_update:
                    value = getattr(um, field, None)
                    if value is not None:
                        setattr(existing, field, value)
                
                to_update.append(existing)
            else:
                user_max_data = {
                    "user_id": user_id,
                    "exercise_id": exercise_id,
                    "exercise_name": exercise_names.get(exercise_id, "Unknown"),
                    "max_weight": um.max_weight,
                    "rep_max": rep_max,
                    "date": dt,
                    "true_1rm": um.true_1rm,
                    "verified_1rm": um.verified_1rm,
                    "source": um.source,
                }
                to_create.append(user_max_data)

            touched_pairs.add((exercise_id, dt))

        if to_update:
            self.repo.bulk_update_user_maxes(to_update)
        
        if to_create:
            results = self.repo.bulk_create_user_maxes(to_create)
        else:
            results = to_update

        if touched_pairs:
            self.repo.recompute_daily_agg_batch(user_id, list(touched_pairs))

        self.db.commit()
        return results

    def get_weak_muscles_analysis(self, user_id: str, **params) -> dict:
        try:
            daily_rows = self.repo.get_daily_agg_for_user(user_id)
            precomputed_ex_strength = aggregate_exercise_strength_from_daily_agg(daily_rows) if daily_rows else None
            
            user_maxes = None
            if not precomputed_ex_strength or params.get('force_raw_data', False):
                user_maxes = self.repo.get_user_maxes_for_analysis(user_id)
            
            profile = compute_weak_muscles(
                user_maxes=user_maxes or [],  # Пустой список если None
                precomputed_ex_strength=precomputed_ex_strength,
                **params
            )
            return profile
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Analysis failed: {e}")
            raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    def purge_user_data(self, user_id: str) -> dict:
        self.repo.purge_user_data(user_id)
        self.db.commit()
        return {"status": "ok"}
