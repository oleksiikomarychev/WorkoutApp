from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from datetime import datetime, timedelta
from typing import List, Optional
import math
import os
import logging
import requests

from ..models.calendar import (
    AppliedCalendarPlan,
    CalendarPlan,
    Mesocycle,
    Microcycle,
    CalendarPlanInstance,
)
from ..models.workout import Workout
from ..models.exercises import ExerciseInstance
from ..schemas.calendar_plan import (
    AppliedCalendarPlanResponse,
    CalendarPlanResponse,
    ApplyPlanComputeSettings,
)
from ..schemas.user_max import UserMaxResponse
from .calendar_plan_service import CalendarPlanService
from ..workout_calculation import WorkoutCalculator
from ..models.user_max import UserMax as UserMaxModel
from ..models.exercises import ExerciseList as ExerciseListModel

logger = logging.getLogger(__name__)


class AppliedCalendarPlanService:
    def __init__(self, db: Session):
        self.db = db

    def _get_base_candidates(self) -> list[str]:
        """Return ordered base URLs to try for fetching user-max data.
        Preference order:
        1) USER_MAX_SERVICE_URL env (direct service)
        2) GATEWAY_URL env (gateway base)
        3) Docker-internal defaults
        4) Localhost defaults (dev)
        """
        candidates: list[str] = []
        um_env = os.getenv("USER_MAX_SERVICE_URL")
        if um_env:
            candidates.append(um_env.rstrip("/"))  # e.g. http://user-max-service:8003
        gw_env = os.getenv("GATEWAY_URL")
        if gw_env:
            candidates.append(
                gw_env.rstrip("/")
            )  # e.g. http://gateway:8000 or http://127.0.0.1:8010
        # sensible fallbacks
        candidates.extend(
            [
                "http://user-max-service:8003",
                "http://gateway:8000",
                "http://localhost:8010",
                "http://127.0.0.1:8010",
                "http://localhost:8003",
            ]
        )
        # de-duplicate while preserving order
        seen = set()
        unique: list[str] = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                unique.append(c)
        return unique

    def _fetch_and_sync_user_maxes_for_exercises(
        self, exercise_ids: set[int], user_id: str
    ) -> list[UserMaxModel]:
        """Fetch user-max records by exercise_id from user-max-service via gateway or direct URL
        and ensure they exist locally. Returns the local SQLAlchemy entities created/found.
        """
        if not exercise_ids:
            return []

        session = requests.Session()
        session.headers.update(
            {"Content-Type": "application/json", "X-User-Id": user_id}
        )

        created: list[UserMaxModel] = []
        bases = self._get_base_candidates()
        for ex_id in exercise_ids:
            payload = None
            # Try each base until one returns data
            for base in bases:
                try:
                    # Determine path shape based on whether base looks like gateway or direct service
                    if (
                        base.endswith(":8003")
                        or base.rsplit("/", 1)[-1].startswith("user-max-service")
                        or "/api/v1/user-maxes" in base
                    ):
                        # direct user-max-service
                        url = f"{base}/api/v1/user-maxes/by_exercise/{ex_id}"
                    else:
                        # gateway
                        url = f"{base}/api/v1/user-max/by_exercise/{ex_id}"
                    r = session.get(url, timeout=2.0)
                    if r.status_code == 200:
                        data = r.json()
                        if isinstance(data, list) and data:
                            payload = data[0]
                            break
                except Exception:
                    # try next base silently
                    continue

            if not payload:
                logger.info(f"No remote user-max found for exercise_id={ex_id}")
                continue

            # Ensure local presence (prefer keeping same ID for consistency across services)
            local = self.db.get(UserMaxModel, payload.get("id"))
            if not local:
                try:
                    local = UserMaxModel(
                        id=payload.get("id"),
                        exercise_id=payload.get("exercise_id"),
                        max_weight=payload.get("max_weight"),
                        rep_max=payload.get("rep_max"),
                    )
                    self.db.add(local)
                    # flush to assign PK and validate FKs early
                    self.db.flush()
                    created.append(local)
                except Exception as e:
                    logger.warning(
                        f"Failed to sync remote user-max id={payload.get('id')} ex={ex_id}: {e}"
                    )
                    self.db.rollback()
                    continue
            else:
                created.append(local)

        if created:
            try:
                self.db.commit()
            except Exception:
                self.db.rollback()
        return created

    def _ensure_exercises_present(self, exercise_ids: set[int]) -> None:
        """Ensure ExerciseList rows exist locally for given IDs by fetching from exercises-service.
        Tries multiple base URLs (envs/gateway/direct). Inserts minimal fields if missing.
        """
        if not exercise_ids:
            return
        # Determine bases: prefer EXERCISES_SERVICE_URL, then GATEWAY_URL, then sensible fallbacks
        bases: list[str] = []
        ex_env = os.getenv("EXERCISES_SERVICE_URL")
        if ex_env:
            bases.append(ex_env.rstrip("/"))  # e.g. http://exercises-service:8002
        gw_env = os.getenv("GATEWAY_URL")
        if gw_env:
            bases.append(gw_env.rstrip("/"))  # e.g. http://gateway:8000
        bases.extend(
            [
                "http://exercises-service:8002",
                "http://gateway:8000",
                "http://localhost:8010",
                "http://127.0.0.1:8010",
                "http://localhost:8002",
            ]
        )

        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})

        for ex_id in exercise_ids:
            if self.db.get(ExerciseListModel, ex_id):
                continue
            payload = None
            for base in bases:
                try:
                    # exercises-service exposes /api/v1/exercises/list/{id}; gateway proxies the same path
                    url = f"{base}/api/v1/exercises/list/{ex_id}"
                    r = session.get(url, timeout=2.0)
                    if r.status_code == 200:
                        payload = r.json()
                        break
                except Exception:
                    continue
            if not payload:
                logger.info(
                    f"Exercise definition id={ex_id} not found via remote; skipping local insert"
                )
                continue
            try:
                local = ExerciseListModel(
                    id=payload.get("id"),
                    name=payload.get("name"),
                    muscle_group=payload.get("muscle_group"),
                    equipment=payload.get("equipment"),
                    target_muscles=payload.get("target_muscles"),
                    synergist_muscles=payload.get("synergist_muscles"),
                    movement_type=payload.get("movement_type"),
                    region=payload.get("region"),
                )
                self.db.add(local)
                # flush to validate and reserve PK
                self.db.flush()
            except Exception as e:
                logger.warning(f"Failed to insert ExerciseList id={ex_id}: {e}")
                self.db.rollback()
                continue

    def apply_plan(
        self,
        plan_id: int,
        user_id: str,
        user_max_ids: List[int],
        compute: ApplyPlanComputeSettings,
    ) -> AppliedCalendarPlanResponse:
        """Применение плана пользователем с настройками вычислений и генерацией тренировок"""
        # План должен быть либо публичным (user_id is None), либо принадлежать пользователю
        base_plan = (
            self.db.query(CalendarPlan)
            .filter(
                CalendarPlan.id == plan_id,
                or_(CalendarPlan.user_id == user_id, CalendarPlan.user_id.is_(None)),
            )
            .first()
        )
        if not base_plan:
            raise ValueError(f"План с ID {plan_id} не найден")

        # Получаем UserMax из базы данных.
        # В локальных тестах допускаем отсутствие частей ID — используем доступные записи без ошибки.
        user_maxes = []
        if user_max_ids:
            user_maxes = (
                self.db.query(UserMaxModel)
                .filter(UserMaxModel.id.in_(user_max_ids))
                .all()
            )

        # Определяем, есть ли иерархическая структура (мезо/микро)
        mesocycles = (
            self.db.query(Mesocycle)
            .filter(Mesocycle.calendar_plan_id == plan_id)
            .order_by(Mesocycle.order_index.asc(), Mesocycle.id.asc())
            .all()
        )

        # Собираем список требуемых упражнений из структуры, если она есть, иначе из планового schedule
        required_exercises = set()
        if mesocycles:
            microcycles = (
                self.db.query(Microcycle)
                .filter(Microcycle.mesocycle_id.in_([m.id for m in mesocycles]))
                .order_by(Microcycle.order_index.asc(), Microcycle.id.asc())
                .all()
            )
            for mc in microcycles:
                for day in (mc.schedule or {}).values():
                    for exercise in day:
                        required_exercises.add(exercise["exercise_id"])
        else:
            for day in base_plan.schedule.values():
                for exercise in day:
                    required_exercises.add(exercise["exercise_id"])

        max_exercises = set(um.exercise_id for um in user_maxes)
        missing_exercises = required_exercises - max_exercises
        if missing_exercises:
            logger.info(
                f"Missing user maxes for exercises: {missing_exercises}. Trying to fetch via user-max-service..."
            )
            fetched = self._fetch_and_sync_user_maxes_for_exercises(
                missing_exercises, user_id
            )
            if fetched:
                user_maxes.extend(fetched)
                max_exercises = set(um.exercise_id for um in user_maxes)
                missing_exercises = required_exercises - max_exercises
        if missing_exercises:
            raise ValueError(f"Не указаны max для упражнений: {missing_exercises}")

        # Ensure exercise definitions exist locally to satisfy FK on ExerciseInstance
        self._ensure_exercises_present(required_exercises)

        # Ensure all exercise definitions referenced by the plan exist locally to satisfy FK
        self._ensure_exercises_present(required_exercises)

        # Deactivate all other active plans for the user
        self.db.query(AppliedCalendarPlan).filter(
            AppliedCalendarPlan.is_active.is_(True)
        ).update({"is_active": False})

        # Create the new applied plan
        applied_plan = AppliedCalendarPlan(
            calendar_plan_id=plan_id,
            user_id=user_id,
            start_date=compute.start_date or datetime.utcnow(),
            user_maxes=user_maxes,
        )
        # Вычисляем дату окончания: если есть микроциклы, считаем по количеству дней, иначе по weeks
        if mesocycles:
            # Получим все микроциклы снова с порядком (или используем вычисленные выше)
            if "microcycles" not in locals():
                microcycles = (
                    self.db.query(Microcycle)
                    .filter(Microcycle.mesocycle_id.in_([m.id for m in mesocycles]))
                    .order_by(Microcycle.order_index.asc(), Microcycle.id.asc())
                    .all()
                )
            total_days = 0
            for mc in microcycles:
                # Предпочитаем явно заданную длину микроцикла (days_count), иначе считаем по количеству дней с тренировками
                if mc.days_count is not None:
                    total_days += mc.days_count
                else:
                    total_days += len((mc.schedule or {}))
            applied_plan.end_date = applied_plan.start_date + timedelta(days=total_days)
        else:
            applied_plan.calculate_end_date(base_plan.duration_weeks)

        self.db.add(applied_plan)
        self.db.commit()
        self.db.refresh(applied_plan)

        # Создаем расписание с расчетом всех параметров сета
        calculated_schedule = {}

        # Helper: rounding function
        def round_to_step(value: float) -> float:
            step = compute.rounding_step
            mode = (
                compute.rounding_mode.value
                if hasattr(compute, "rounding_mode")
                else "nearest"
            )
            if step <= 0:
                return value
            ratio = value / step
            if mode == "floor":
                return math.floor(ratio) * step
            elif mode == "ceil":
                return math.ceil(ratio) * step
            else:
                return round(ratio) * step

        # Generate linked workouts if requested
        plan_order = 0
        if mesocycles:
            # Build schedule from microcycles
            # Fetch microcycles grouped by mesocycle preserving order
            meso_id_to_micro = {}
            microcycles = (
                self.db.query(Microcycle)
                .filter(Microcycle.mesocycle_id.in_([m.id for m in mesocycles]))
                .order_by(
                    Microcycle.mesocycle_id.asc(),
                    Microcycle.order_index.asc(),
                    Microcycle.id.asc(),
                )
                .all()
            )
            for mc in microcycles:
                meso_id_to_micro.setdefault(mc.mesocycle_id, []).append(mc)

            # Текущие эффективные 1RM пользователя (могут меняться нормализацией)
            # База берётся из истинного 1RM; если его нет, используем max_weight как приближение
            effective_1rms: dict[int, float] = {}
            for um in user_maxes:
                base_true = WorkoutCalculator.get_true_1rm_from_user_max(um)
                effective_1rms[um.exercise_id] = float(
                    base_true if base_true is not None else um.max_weight
                )

            def apply_normalization_to_effective(
                effective: dict[int, float], value: Optional[float], unit: Optional[str]
            ):
                if value is None or unit is None:
                    return
                if unit == "%":
                    factor = 1.0 + (value / 100.0)
                    for k in list(effective.keys()):
                        effective[k] = max(0.0, effective[k] * factor)
                elif unit == "kg":
                    for k in list(effective.keys()):
                        effective[k] = max(0.0, effective[k] + value)

            for mi, meso in enumerate(mesocycles, start=1):
                # Применяем нормализацию мезоцикла в начале его блока
                apply_normalization_to_effective(
                    effective_1rms, meso.normalization_value, meso.normalization_unit
                )
                for mci, mc in enumerate(meso_id_to_micro.get(meso.id, []), start=1):
                    # day_key order relies on insertion order of JSON
                    for di, (day_key, exercises) in enumerate(
                        (mc.schedule or {}).items(), start=1
                    ):
                        scheduled_dt = (
                            (applied_plan.start_date + timedelta(days=plan_order))
                            if compute.generate_workouts
                            else None
                        )
                        label = f"M{mi}-MC{mci}-D{di}: {day_key}"

                        calculated_schedule[label] = []

                        workout_entity: Optional[Workout] = None
                        if compute.generate_workouts:
                            workout_entity = Workout(
                                name=f"{base_plan.name} - {label}",
                                applied_plan_id=applied_plan.id,
                                plan_order_index=plan_order,
                                scheduled_for=scheduled_dt,
                                # ensure freshly generated workouts are NOT completed
                                completed_at=None,
                                status=None,
                            )
                            self.db.add(workout_entity)
                            self.db.flush()

                        # Build exercises
                        for exercise in exercises:
                            user_max = next(
                                (
                                    um
                                    for um in user_maxes
                                    if um.exercise_id == exercise["exercise_id"]
                                ),
                                None,
                            )
                            if not user_max:
                                continue

                            calculated_sets = []
                            for set_data in exercise["sets"]:
                                intensity = set_data.get("intensity")
                                effort = set_data.get("effort")
                                volume = set_data.get("volume")

                                if intensity is not None and effort is not None:
                                    volume = WorkoutCalculator.get_volume(
                                        intensity=intensity, effort=effort
                                    )
                                elif volume is not None and effort is not None:
                                    intensity = WorkoutCalculator.get_intensity(
                                        volume=volume, effort=effort
                                    )
                                elif volume is not None and intensity is not None:
                                    effort = WorkoutCalculator.get_effort(
                                        volume=volume, intensity=intensity
                                    )

                                weight = None
                                if compute.compute_weights and intensity is not None:
                                    # Используем эффективный (нормализованный) 1RM
                                    eff = effective_1rms.get(user_max.exercise_id)
                                    if eff is None:
                                        # на всякий случай fallback к текущей логике
                                        true_1rm = WorkoutCalculator.get_true_1rm_from_user_max(
                                            user_max
                                        )
                                        eff = (
                                            float(true_1rm)
                                            if true_1rm is not None
                                            else float(user_max.max_weight)
                                        )
                                        effective_1rms[user_max.exercise_id] = eff
                                    raw = eff * (intensity / 100.0)
                                    weight = round_to_step(raw)

                                calculated_sets.append(
                                    {
                                        "intensity": intensity,
                                        "effort": effort,
                                        "volume": volume,
                                        "working_weight": weight,
                                        "weight": weight,
                                    }
                                )

                            calculated_exercise = {
                                "exercise_id": exercise["exercise_id"],
                                "sets": calculated_sets,
                            }
                            calculated_schedule[label].append(calculated_exercise)

                            if compute.generate_workouts and workout_entity is not None:
                                instance = ExerciseInstance(
                                    workout_id=workout_entity.id,
                                    exercise_list_id=exercise["exercise_id"],
                                    user_max_id=user_max.id,
                                    sets=[
                                        {
                                            "id": idx + 1,
                                            "weight": s.get("weight"),
                                            "reps": s.get("volume"),
                                            "rpe": s.get("effort"),
                                            "volume": s.get("volume"),
                                            "intensity": s.get("intensity"),
                                        }
                                        for idx, s in enumerate(calculated_sets)
                                    ],
                                )
                                self.db.add(instance)
                        plan_order += 1

                    # После завершения микроцикла применяем его нормализацию для последующих дней
                    apply_normalization_to_effective(
                        effective_1rms, mc.normalization_value, mc.normalization_unit
                    )
        else:
            for day_key, exercises in base_plan.schedule.items():
                # Calculate schedule date for this day order
                scheduled_dt = (
                    (applied_plan.start_date + timedelta(days=plan_order))
                    if compute.generate_workouts
                    else None
                )

                # Calculate the schedule representation for response
                calculated_schedule[day_key] = []

                # Optionally create a Workout entity linked to the applied plan
                workout_entity: Optional[Workout] = None
                if compute.generate_workouts:
                    workout_entity = Workout(
                        name=f"{base_plan.name} - {day_key}",
                        applied_plan_id=applied_plan.id,
                        plan_order_index=plan_order,
                        scheduled_for=scheduled_dt,
                        # ensure freshly generated workouts are NOT completed
                        completed_at=None,
                        status=None,
                    )
                    self.db.add(workout_entity)
                    self.db.flush()  # Ensure id is available

                # Build exercises
                for exercise in exercises:
                    # Найдем соответствующий UserMax
                    user_max = next(
                        (
                            um
                            for um in user_maxes
                            if um.exercise_id == exercise["exercise_id"]
                        ),
                        None,
                    )
                    if not user_max:
                        continue

                    calculated_sets = []
                    for set_data in exercise["sets"]:
                        intensity = set_data.get("intensity")
                        effort = set_data.get("effort")
                        volume = set_data.get("volume")

                        # Вычисляем недостающие параметры
                        if intensity is not None and effort is not None:
                            volume = WorkoutCalculator.get_volume(
                                intensity=intensity, effort=effort
                            )
                        elif volume is not None and effort is not None:
                            intensity = WorkoutCalculator.get_intensity(
                                volume=volume, effort=effort
                            )
                        elif volume is not None and intensity is not None:
                            effort = WorkoutCalculator.get_effort(
                                volume=volume, intensity=intensity
                            )

                        weight = None
                        if compute.compute_weights and intensity is not None:
                            true_1rm = WorkoutCalculator.get_true_1rm_from_user_max(
                                user_max
                            )
                            if true_1rm:
                                raw = true_1rm * (intensity / 100.0)
                            else:
                                raw = user_max.max_weight * (intensity / 100.0)
                            weight = round_to_step(raw)

                        # Store for response schedule (working_weight excluded by schema on dump)
                        calculated_sets.append(
                            {
                                "intensity": intensity,
                                "effort": effort,
                                "volume": volume,
                                "working_weight": weight,
                                "weight": weight,
                            }
                        )

                    # Append to schedule for response
                    calculated_exercise = {
                        "exercise_id": exercise["exercise_id"],
                        "sets": calculated_sets,
                    }
                    calculated_schedule[day_key].append(calculated_exercise)

                    # Create ExerciseInstance linked to workout
                    if compute.generate_workouts and workout_entity is not None:
                        instance = ExerciseInstance(
                            workout_id=workout_entity.id,
                            exercise_list_id=exercise["exercise_id"],
                            user_max_id=user_max.id,
                            # Store sets using frontend-compatible keys and stable IDs
                            # reps  <- volume, rpe <- effort
                            # keep volume and intensity for compatibility/analytics
                            sets=[
                                {
                                    "id": idx + 1,
                                    "weight": s.get("weight"),
                                    "reps": s.get("volume"),
                                    "rpe": s.get("effort"),
                                    "volume": s.get("volume"),
                                    "intensity": s.get("intensity"),
                                }
                                for idx, s in enumerate(calculated_sets)
                            ],
                        )
                        self.db.add(instance)

                plan_order += 1

        if compute.generate_workouts:
            self.db.commit()
            self.db.refresh(applied_plan)

        # Преобразуем SQLAlchemy модели в Pydantic модели
        # Prepare next workout summary (first not completed by order)
        next_summary = None
        if compute.generate_workouts:
            next_w = (
                self.db.query(Workout)
                .filter(Workout.applied_plan_id == applied_plan.id)
                .filter(Workout.completed_at.is_(None))
                .order_by(Workout.plan_order_index.asc())
                .first()
            )
            if next_w:
                next_summary = AppliedCalendarPlanResponse.NextWorkoutSummary(
                    id=next_w.id,
                    name=next_w.name,
                    scheduled_for=next_w.scheduled_for,
                    plan_order_index=next_w.plan_order_index,
                )

        applied_plan_response = AppliedCalendarPlanResponse(
            id=applied_plan.id,
            calendar_plan_id=applied_plan.calendar_plan_id,
            start_date=applied_plan.start_date,
            end_date=applied_plan.end_date,
            is_active=applied_plan.is_active,
            calendar_plan=CalendarPlanResponse(
                id=base_plan.id,
                name=base_plan.name,
                schedule=calculated_schedule,
                duration_weeks=base_plan.duration_weeks,
                is_active=base_plan.is_active,
            ),
            user_maxes=[
                UserMaxResponse(
                    id=um.id,
                    exercise_id=um.exercise_id,
                    max_weight=um.max_weight,
                    rep_max=um.rep_max,
                )
                for um in user_maxes
            ],
            user_max_ids=list(user_max_ids or []),
            next_workout=next_summary,
        )

        return applied_plan_response

    def apply_plan_from_instance(
        self,
        instance_id: int,
        user_id: str,
        user_max_ids: List[int],
        compute: ApplyPlanComputeSettings,
    ) -> AppliedCalendarPlanResponse:
        """Применение текущей РЕДАКТИРОВАННОЙ версии (instance) вместо исходного плана.
        Использует расписание из `CalendarPlanInstance.schedule` и его duration_weeks для дат,
        генерирует тренировки по аналогии с apply_plan.
        """
        instance = self.db.get(CalendarPlanInstance, instance_id)
        if not instance:
            raise ValueError(f"Instance with ID {instance_id} not found")

        base_plan = instance.source_plan_id and self.db.get(
            CalendarPlan, instance.source_plan_id
        )

        user_maxes = []
        if user_max_ids:
            user_maxes = (
                self.db.query(UserMaxModel)
                .filter(UserMaxModel.id.in_(user_max_ids))
                .all()
            )

        required_exercises = set()
        for exercises in (instance.schedule or {}).values():
            for exercise in exercises:
                required_exercises.add(exercise["exercise_id"])

        max_exercises = set(um.exercise_id for um in user_maxes)
        missing_exercises = required_exercises - max_exercises
        if missing_exercises:
            logger.info(
                f"Missing user maxes for exercises: {missing_exercises}. Trying to fetch via user-max-service..."
            )
            fetched = self._fetch_and_sync_user_maxes_for_exercises(
                missing_exercises, user_id
            )
            if fetched:
                user_maxes.extend(fetched)
                max_exercises = set(um.exercise_id for um in user_maxes)
                missing_exercises = required_exercises - max_exercises
        if missing_exercises:
            raise ValueError(f"Не указаны max для упражнений: {missing_exercises}")

        self._ensure_exercises_present(required_exercises)

        calendar_plan_id = (
            instance.source_plan_id
            if instance.source_plan_id is not None
            else (base_plan.id if base_plan else None)
        )
        if calendar_plan_id is None:
            raise ValueError(
                "Невозможно применить: у экземпляра отсутствует исходный план (source_plan_id)"
            )

        self.db.query(AppliedCalendarPlan).filter(
            AppliedCalendarPlan.user_id == user_id,
            AppliedCalendarPlan.is_active.is_(True),
        ).update({"is_active": False})

        applied_plan = AppliedCalendarPlan(
            calendar_plan_id=calendar_plan_id,
            user_id=user_id,
            start_date=compute.start_date or datetime.utcnow(),
            user_maxes=user_maxes,
        )

        if instance.schedule:
            total_days = len(instance.schedule)
            applied_plan.end_date = applied_plan.start_date + timedelta(days=total_days)
        else:
            applied_plan.calculate_end_date(instance.duration_weeks)

        self.db.add(applied_plan)
        self.db.commit()
        self.db.refresh(applied_plan)

        calculated_schedule = {}

        def round_to_step(value: float) -> float:
            step = compute.rounding_step
            mode = (
                compute.rounding_mode.value
                if hasattr(compute, "rounding_mode")
                else "nearest"
            )
            if step <= 0:
                return value
            ratio = value / step
            if mode == "floor":
                return math.floor(ratio) * step
            elif mode == "ceil":
                return math.ceil(ratio) * step
            return round(ratio) * step

        plan_order = 0
        for day_key, exercises in (instance.schedule or {}).items():
            scheduled_dt = (
                (applied_plan.start_date + timedelta(days=plan_order))
                if compute.generate_workouts
                else None
            )
            label = day_key
            calculated_schedule[label] = []

            workout_entity: Optional[Workout] = None
            if compute.generate_workouts:
                workout_entity = Workout(
                    name=f"{(base_plan.name if base_plan else instance.name)} - {label}",
                    applied_plan_id=applied_plan.id,
                    plan_order_index=plan_order,
                    scheduled_for=scheduled_dt,
                    completed_at=None,
                    status=None,
                )
                self.db.add(workout_entity)
                self.db.flush()

            for exercise in exercises:
                user_max = next(
                    (
                        um
                        for um in user_maxes
                        if um.exercise_id == exercise["exercise_id"]
                    ),
                    None,
                )
                if not user_max:
                    continue

                calculated_sets = []
                for set_data in exercise["sets"]:
                    intensity = set_data.get("intensity")
                    effort = set_data.get("effort")
                    volume = set_data.get("volume")

                    if intensity is not None and effort is not None:
                        volume = WorkoutCalculator.get_volume(
                            intensity=intensity, effort=effort
                        )
                    elif volume is not None and effort is not None:
                        intensity = WorkoutCalculator.get_intensity(
                            volume=volume, effort=effort
                        )
                    elif volume is not None and intensity is not None:
                        effort = WorkoutCalculator.get_effort(
                            volume=volume, intensity=intensity
                        )

                    weight = None
                    if compute.compute_weights and intensity is not None:
                        true_1rm = WorkoutCalculator.get_true_1rm_from_user_max(
                            user_max
                        )
                        raw = (true_1rm if true_1rm else user_max.max_weight) * (
                            intensity / 100.0
                        )
                        weight = round_to_step(raw)

                    calculated_sets.append(
                        {
                            "intensity": intensity,
                            "effort": effort,
                            "volume": volume,
                            "working_weight": weight,
                            "weight": weight,
                        }
                    )

                calculated_schedule[label].append(
                    {"exercise_id": exercise["exercise_id"], "sets": calculated_sets}
                )

                if compute.generate_workouts and workout_entity:
                    instance_ex = ExerciseInstance(
                        workout_id=workout_entity.id,
                        exercise_list_id=exercise["exercise_id"],
                        user_max_id=user_max.id,
                        sets=[
                            {
                                "id": idx + 1,
                                "weight": s.get("weight"),
                                "reps": s.get("volume"),
                                "rpe": s.get("effort"),
                                "volume": s.get("volume"),
                                "intensity": s.get("intensity"),
                            }
                            for idx, s in enumerate(calculated_sets)
                        ],
                    )
                    self.db.add(instance_ex)
            plan_order += 1

        if compute.generate_workouts:
            self.db.commit()
            self.db.refresh(applied_plan)

        next_summary = None
        if compute.generate_workouts:
            next_w = (
                self.db.query(Workout)
                .filter(
                    Workout.applied_plan_id == applied_plan.id,
                    Workout.completed_at.is_(None),
                )
                .order_by(Workout.plan_order_index.asc())
                .first()
            )
            if next_w:
                next_summary = AppliedCalendarPlanResponse.NextWorkoutSummary(
                    id=next_w.id,
                    name=next_w.name,
                    scheduled_for=next_w.scheduled_for,
                    plan_order_index=next_w.plan_order_index,
                )

        applied_plan_response = AppliedCalendarPlanResponse(
            id=applied_plan.id,
            calendar_plan_id=applied_plan.calendar_plan_id,
            start_date=applied_plan.start_date,
            end_date=applied_plan.end_date,
            is_active=applied_plan.is_active,
            calendar_plan=CalendarPlanResponse(
                id=base_plan.id if base_plan else instance.id,
                name=base_plan.name if base_plan else instance.name,
                schedule=calculated_schedule,
                duration_weeks=instance.duration_weeks,
                is_active=True,
            ),
            user_maxes=[
                UserMaxResponse(
                    id=um.id,
                    exercise_id=um.exercise_id,
                    max_weight=um.max_weight,
                    rep_max=um.rep_max,
                )
                for um in user_maxes
            ],
            user_max_ids=list(user_max_ids or []),
            next_workout=next_summary,
        )

        return applied_plan_response

    def get_applied_plan_by_id(
        self, plan_id: int, user_id: str
    ) -> Optional[AppliedCalendarPlan]:
        """Get a single applied plan by ID with all relationships eagerly loaded."""
        return (
            self.db.query(AppliedCalendarPlan)
            .options(
                joinedload(AppliedCalendarPlan.calendar_plan)
                .joinedload(CalendarPlan.mesocycles)
                .joinedload(Mesocycle.microcycles),
                joinedload(AppliedCalendarPlan.user_maxes),
                joinedload(AppliedCalendarPlan.workouts),
            )
            .filter(
                AppliedCalendarPlan.id == plan_id,
                AppliedCalendarPlan.user_id == user_id,
            )
            .first()
        )

    def get_user_applied_plans(self, user_id: str) -> List[dict]:
        """Get all applied plans for a user with minimal data for list view.
        Returns plain dicts matching AppliedCalendarPlanSummaryResponse.
        """
        plans: List[AppliedCalendarPlan] = (
            self.db.query(AppliedCalendarPlan)
            .filter(AppliedCalendarPlan.user_id == user_id)
            .options(
                joinedload(AppliedCalendarPlan.calendar_plan),
                joinedload(AppliedCalendarPlan.workouts).load_only(
                    Workout.id,
                    Workout.name,
                    Workout.completed_at,
                    Workout.plan_order_index,
                    Workout.scheduled_for,
                ),
            )
            .order_by(AppliedCalendarPlan.start_date.desc())
            .all()
        )

        summaries: List[dict] = []
        for p in plans:
            # compute next workout: first by plan_order_index where not completed
            next_w = None
            if p.workouts:
                ordered = sorted(p.workouts, key=lambda w: (w.plan_order_index or 0))
                for w in ordered:
                    if getattr(w, "completed_at", None) is None:
                        next_w = w
                        break
            next_summary = None
            if next_w is not None:
                next_summary = {
                    "id": next_w.id,
                    "name": next_w.name,
                    "scheduled_for": next_w.scheduled_for,
                    "plan_order_index": next_w.plan_order_index,
                }

            summaries.append(
                {
                    "id": p.id,
                    "calendar_plan_id": p.calendar_plan_id,
                    "start_date": p.start_date,
                    "end_date": p.end_date,
                    "is_active": p.is_active,
                    "calendar_plan": {
                        "id": p.calendar_plan.id
                        if p.calendar_plan
                        else p.calendar_plan_id,
                        "name": p.calendar_plan.name if p.calendar_plan else "",
                    },
                    "next_workout": next_summary,
                }
            )

        return summaries

    def get_active_plan(self, user_id: str) -> Optional[AppliedCalendarPlanResponse]:
        """Get the currently active plan with full details."""
        active_plan = (
            self.db.query(AppliedCalendarPlan)
            .options(
                joinedload(AppliedCalendarPlan.calendar_plan)
                .joinedload(CalendarPlan.mesocycles)
                .joinedload(Mesocycle.microcycles),
                joinedload(AppliedCalendarPlan.user_maxes),
                joinedload(AppliedCalendarPlan.workouts),
            )
            .filter(
                and_(
                    AppliedCalendarPlan.is_active.is_(True),
                    AppliedCalendarPlan.user_id == user_id,
                )
            )
            .first()
        )

        if active_plan:
            next_w = next(
                (
                    w
                    for w in sorted(
                        active_plan.workouts, key=lambda x: x.plan_order_index
                    )
                    if w.completed_at is None
                ),
                None,
            )
            next_summary = None
            if next_w:
                next_summary = AppliedCalendarPlanResponse.NextWorkoutSummary(
                    id=next_w.id,
                    name=next_w.name,
                    scheduled_for=next_w.scheduled_for,
                    plan_order_index=next_w.plan_order_index,
                )

            plan_service = CalendarPlanService(self.db)
            return AppliedCalendarPlanResponse(
                id=active_plan.id,
                calendar_plan_id=active_plan.calendar_plan_id,
                start_date=active_plan.start_date,
                end_date=active_plan.end_date,
                is_active=active_plan.is_active,
                calendar_plan=plan_service._get_plan_response(
                    active_plan.calendar_plan, user_id
                ),
                user_maxes=[
                    UserMaxResponse(
                        id=um.id,
                        exercise_id=um.exercise_id,
                        max_weight=um.max_weight,
                        rep_max=um.rep_max,
                    )
                    for um in active_plan.user_maxes
                ],
                user_max_ids=[um.id for um in active_plan.user_maxes],
                next_workout=next_summary,
            )
        return None
