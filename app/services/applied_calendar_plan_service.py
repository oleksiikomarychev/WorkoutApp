from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func
from datetime import datetime, timedelta
from typing import List, Optional
import math

from app.models.calendar import AppliedCalendarPlan, CalendarPlan, Mesocycle, Microcycle, CalendarPlanInstance
from app.models.workout import Workout
from app.models.exercises import ExerciseInstance
from app.schemas.calendar_plan import (
    AppliedCalendarPlanResponse,
    CalendarPlanResponse,
    ApplyPlanComputeSettings,
)
from app.schemas.user_max import UserMaxResponse
from app.workout_calculation import WorkoutCalculator
from app.models.user_max import UserMax as UserMaxModel

class AppliedCalendarPlanService:
    def __init__(self, db: Session):
        self.db = db

    def apply_plan(self, plan_id: int, user_max_ids: List[int], compute: ApplyPlanComputeSettings) -> AppliedCalendarPlanResponse:
        """Применение плана пользователем с настройками вычислений и генерацией тренировок"""
        # Получаем базовый план
        base_plan = self.db.get(CalendarPlan, plan_id)
        if not base_plan:
            raise ValueError(f"План с ID {plan_id} не найден")

        # Получаем UserMax из базы данных
        user_maxes = self.db.query(UserMaxModel).filter(UserMaxModel.id.in_(user_max_ids)).all()
        
        # Проверяем, что все UserMax найдены
        missing_ids = set(user_max_ids) - {um.id for um in user_maxes}
        if missing_ids:
            raise ValueError(f"UserMax records not found for IDs: {missing_ids}")

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
                        required_exercises.add(exercise['exercise_id'])
        else:
            for day in base_plan.schedule.values():
                for exercise in day:
                    required_exercises.add(exercise['exercise_id'])

        max_exercises = set(um.exercise_id for um in user_maxes)
        missing_exercises = required_exercises - max_exercises
        if missing_exercises:
            raise ValueError(f"Не указаны max для упражнений: {missing_exercises}")

        # Создаем примененный план
        applied_plan = AppliedCalendarPlan(
            calendar_plan_id=plan_id,
            start_date=compute.start_date or datetime.utcnow(),
            user_maxes=user_maxes
        )
        # Вычисляем дату окончания: если есть микроциклы, считаем по количеству дней, иначе по weeks
        if mesocycles:
            # Получим все микроциклы снова с порядком (или используем вычисленные выше)
            if 'microcycles' not in locals():
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
            mode = compute.rounding_mode.value if hasattr(compute, 'rounding_mode') else 'nearest'
            if step <= 0:
                return value
            ratio = value / step
            if mode == 'floor':
                return math.floor(ratio) * step
            elif mode == 'ceil':
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
                .order_by(Microcycle.mesocycle_id.asc(), Microcycle.order_index.asc(), Microcycle.id.asc())
                .all()
            )
            for mc in microcycles:
                meso_id_to_micro.setdefault(mc.mesocycle_id, []).append(mc)

            # Текущие эффективные 1RM пользователя (могут меняться нормализацией)
            # База берётся из истинного 1RM; если его нет, используем max_weight как приближение
            effective_1rms: dict[int, float] = {}
            for um in user_maxes:
                base_true = WorkoutCalculator.get_true_1rm_from_user_max(um)
                effective_1rms[um.exercise_id] = float(base_true if base_true is not None else um.max_weight)

            def apply_normalization_to_effective(effective: dict[int, float], value: Optional[float], unit: Optional[str]):
                if value is None or unit is None:
                    return
                if unit == '%':
                    factor = 1.0 + (value / 100.0)
                    for k in list(effective.keys()):
                        effective[k] = max(0.0, effective[k] * factor)
                elif unit == 'kg':
                    for k in list(effective.keys()):
                        effective[k] = max(0.0, effective[k] + value)

            for mi, meso in enumerate(mesocycles, start=1):
                # Применяем нормализацию мезоцикла в начале его блока
                apply_normalization_to_effective(effective_1rms, meso.normalization_value, meso.normalization_unit)
                for mci, mc in enumerate(meso_id_to_micro.get(meso.id, []), start=1):
                    # day_key order relies on insertion order of JSON
                    for di, (day_key, exercises) in enumerate((mc.schedule or {}).items(), start=1):
                        scheduled_dt = (applied_plan.start_date + timedelta(days=plan_order)) if compute.generate_workouts else None
                        label = f"M{mi}-MC{mci}-D{di}: {day_key}"

                        calculated_schedule[label] = []

                        workout_entity: Optional[Workout] = None
                        if compute.generate_workouts:
                            workout_entity = Workout(
                                name=f"{base_plan.name} - {label}",
                                applied_plan_id=applied_plan.id,
                                plan_order_index=plan_order,
                                scheduled_for=scheduled_dt,
                            )
                            self.db.add(workout_entity)
                            self.db.flush()

                        # Build exercises
                        for exercise in exercises:
                            user_max = next((um for um in user_maxes if um.exercise_id == exercise['exercise_id']), None)
                            if not user_max:
                                continue

                            calculated_sets = []
                            for set_data in exercise['sets']:
                                intensity = set_data.get('intensity')
                                effort = set_data.get('effort')
                                volume = set_data.get('volume')

                                if intensity is not None and effort is not None:
                                    volume = WorkoutCalculator.get_volume(intensity=intensity, effort=effort)
                                elif volume is not None and effort is not None:
                                    intensity = WorkoutCalculator.get_intensity(volume=volume, effort=effort)
                                elif volume is not None and intensity is not None:
                                    effort = WorkoutCalculator.get_effort(volume=volume, intensity=intensity)

                                weight = None
                                if compute.compute_weights and intensity is not None:
                                    # Используем эффективный (нормализованный) 1RM
                                    eff = effective_1rms.get(user_max.exercise_id)
                                    if eff is None:
                                        # на всякий случай fallback к текущей логике
                                        true_1rm = WorkoutCalculator.get_true_1rm_from_user_max(user_max)
                                        eff = float(true_1rm) if true_1rm is not None else float(user_max.max_weight)
                                        effective_1rms[user_max.exercise_id] = eff
                                    raw = eff * (intensity / 100.0)
                                    weight = round_to_step(raw)

                                calculated_sets.append({
                                    'intensity': intensity,
                                    'effort': effort,
                                    'volume': volume,
                                    'working_weight': weight,
                                    'weight': weight,
                                })

                            calculated_exercise = {
                                'exercise_id': exercise['exercise_id'],
                                'sets': calculated_sets
                            }
                            calculated_schedule[label].append(calculated_exercise)

                            if compute.generate_workouts and workout_entity is not None:
                                instance = ExerciseInstance(
                                    workout_id=workout_entity.id,
                                    exercise_list_id=exercise['exercise_id'],
                                    user_max_id=user_max.id,
                                    sets=[
                                        {
                                            'id': idx + 1,
                                            'weight': s.get('weight'),
                                            'reps': s.get('volume'),
                                            'rpe': s.get('effort'),
                                            'volume': s.get('volume'),
                                            'intensity': s.get('intensity'),
                                        }
                                        for idx, s in enumerate(calculated_sets)
                                    ],
                                )
                                self.db.add(instance)
                        plan_order += 1

                    # После завершения микроцикла применяем его нормализацию для последующих дней
                    apply_normalization_to_effective(effective_1rms, mc.normalization_value, mc.normalization_unit)
        else:
            for day_key, exercises in base_plan.schedule.items():
                # Calculate schedule date for this day order
                scheduled_dt = (applied_plan.start_date + timedelta(days=plan_order)) if compute.generate_workouts else None

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
                    )
                    self.db.add(workout_entity)
                    self.db.flush()  # Ensure id is available

                # Build exercises
                for exercise in exercises:
                    # Найдем соответствующий UserMax
                    user_max = next((um for um in user_maxes if um.exercise_id == exercise['exercise_id']), None)
                    if not user_max:
                        continue

                    calculated_sets = []
                    for set_data in exercise['sets']:
                        intensity = set_data.get('intensity')
                        effort = set_data.get('effort')
                        volume = set_data.get('volume')

                        # Вычисляем недостающие параметры
                        if intensity is not None and effort is not None:
                            volume = WorkoutCalculator.get_volume(intensity=intensity, effort=effort)
                        elif volume is not None and effort is not None:
                            intensity = WorkoutCalculator.get_intensity(volume=volume, effort=effort)
                        elif volume is not None and intensity is not None:
                            effort = WorkoutCalculator.get_effort(volume=volume, intensity=intensity)

                        weight = None
                        if compute.compute_weights and intensity is not None:
                            true_1rm = WorkoutCalculator.get_true_1rm_from_user_max(user_max)
                            if true_1rm:
                                raw = true_1rm * (intensity / 100.0)
                            else:
                                raw = user_max.max_weight * (intensity / 100.0)
                            weight = round_to_step(raw)

                        # Store for response schedule (working_weight excluded by schema on dump)
                        calculated_sets.append({
                            'intensity': intensity,
                            'effort': effort,
                            'volume': volume,
                            'working_weight': weight,
                            'weight': weight,
                        })

                    # Append to schedule for response
                    calculated_exercise = {
                        'exercise_id': exercise['exercise_id'],
                        'sets': calculated_sets
                    }
                    calculated_schedule[day_key].append(calculated_exercise)

                    # Create ExerciseInstance linked to workout
                    if compute.generate_workouts and workout_entity is not None:
                        instance = ExerciseInstance(
                            workout_id=workout_entity.id,
                            exercise_list_id=exercise['exercise_id'],
                            user_max_id=user_max.id,
                            # Store sets using frontend-compatible keys and stable IDs
                            # reps  <- volume, rpe <- effort
                            # keep volume and intensity for compatibility/analytics
                            sets=[
                                {
                                    'id': idx + 1,
                                    'weight': s.get('weight'),
                                    'reps': s.get('volume'),
                                    'rpe': s.get('effort'),
                                    'volume': s.get('volume'),
                                    'intensity': s.get('intensity'),
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
            next_w = self.db.query(Workout) \
                .filter(Workout.applied_plan_id == applied_plan.id) \
                .filter(Workout.completed_at.is_(None)) \
                .order_by(Workout.plan_order_index.asc()) \
                .first()
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
                is_active=base_plan.is_active
            ),
            user_maxes=[
                UserMaxResponse(
                    id=um.id,
                    exercise_id=um.exercise_id,
                    max_weight=um.max_weight,
                    rep_max=um.rep_max
                )
                for um in user_maxes
            ],
            next_workout=next_summary,
        )
        
        return applied_plan_response

    def apply_plan_from_instance(self, instance_id: int, user_max_ids: List[int], compute: ApplyPlanComputeSettings) -> AppliedCalendarPlanResponse:
        """Применение текущей РЕДАКТИРОВАННОЙ версии (instance) вместо исходного плана.
        Использует расписание из `CalendarPlanInstance.schedule` и его duration_weeks для дат,
        генерирует тренировки по аналогии с apply_plan.
        """
        # Получаем instance и связанный базовый план (если есть) для имени
        instance = self.db.get(CalendarPlanInstance, instance_id)
        if not instance:
            raise ValueError(f"Instance with ID {instance_id} not found")

        base_plan = instance.source_plan_id and self.db.get(CalendarPlan, instance.source_plan_id)

        # Получаем UserMax
        user_maxes = self.db.query(UserMaxModel).filter(UserMaxModel.id.in_(user_max_ids)).all()
        missing_ids = set(user_max_ids) - {um.id for um in user_maxes}
        if missing_ids:
            raise ValueError(f"UserMax records not found for IDs: {missing_ids}")

        # Проверяем покрытие упражнений
        required_exercises = set()
        for exercises in (instance.schedule or {}).values():
            for exercise in exercises:
                required_exercises.add(exercise['exercise_id'])
        max_exercises = set(um.exercise_id for um in user_maxes)
        missing_exercises = required_exercises - max_exercises
        if missing_exercises:
            raise ValueError(f"Не указаны max для упражнений: {missing_exercises}")

        # Создаём AppliedCalendarPlan (привязываем к source_plan_id если есть, иначе создаём без связи на реал. план?)
        # Храним ссылку на source_plan_id если доступен, чтобы не ломать схему
        calendar_plan_id = instance.source_plan_id if instance.source_plan_id is not None else (base_plan.id if base_plan else None)
        if calendar_plan_id is None:
            # На случай отсутствия source планов, создадим временный план-заглушку?
            # Здесь проще запретить: без исходного плана невозможно заполнить calendar_plan_id
            raise ValueError("Невозможно применить: у экземпляра отсутствует исходный план (source_plan_id)")

        applied_plan = AppliedCalendarPlan(
            calendar_plan_id=calendar_plan_id,
            start_date=compute.start_date or datetime.utcnow(),
            user_maxes=user_maxes,
        )

        # Даты: считаем по количеству дней instance.schedule, иначе по duration_weeks
        if instance.schedule:
            total_days = len(instance.schedule)
            applied_plan.end_date = applied_plan.start_date + timedelta(days=total_days)
        else:
            applied_plan.calculate_end_date(instance.duration_weeks)

        self.db.add(applied_plan)
        self.db.commit()
        self.db.refresh(applied_plan)

        # Подготовка расчётов
        calculated_schedule = {}

        def round_to_step(value: float) -> float:
            step = compute.rounding_step
            mode = compute.rounding_mode.value if hasattr(compute, 'rounding_mode') else 'nearest'
            if step <= 0:
                return value
            ratio = value / step
            if mode == 'floor':
                return math.floor(ratio) * step
            elif mode == 'ceil':
                return math.ceil(ratio) * step
            else:
                return round(ratio) * step

        plan_order = 0
        # Обходим дни instance в порядке вставки
        for day_key, exercises in (instance.schedule or {}).items():
            scheduled_dt = (applied_plan.start_date + timedelta(days=plan_order)) if compute.generate_workouts else None
            label = day_key
            calculated_schedule[label] = []

            workout_entity: Optional[Workout] = None
            if compute.generate_workouts:
                workout_entity = Workout(
                    name=f"{(base_plan.name if base_plan else instance.name)} - {label}",
                    applied_plan_id=applied_plan.id,
                    plan_order_index=plan_order,
                    scheduled_for=scheduled_dt,
                )
                self.db.add(workout_entity)
                self.db.flush()

            for exercise in exercises:
                user_max = next((um for um in user_maxes if um.exercise_id == exercise['exercise_id']), None)
                if not user_max:
                    continue
                calculated_sets = []
                for set_data in exercise['sets']:
                    intensity = set_data.get('intensity')
                    effort = set_data.get('effort')
                    volume = set_data.get('volume')

                    if intensity is not None and effort is not None:
                        volume = WorkoutCalculator.get_volume(intensity=intensity, effort=effort)
                    elif volume is not None and effort is not None:
                        intensity = WorkoutCalculator.get_intensity(volume=volume, effort=effort)
                    elif volume is not None and intensity is not None:
                        effort = WorkoutCalculator.get_effort(volume=volume, intensity=intensity)

                    weight = None
                    if compute.compute_weights and intensity is not None:
                        true_1rm = WorkoutCalculator.get_true_1rm_from_user_max(user_max)
                        if true_1rm:
                            raw = true_1rm * (intensity / 100.0)
                        else:
                            raw = user_max.max_weight * (intensity / 100.0)
                        weight = round_to_step(raw)

                    calculated_sets.append({
                        'intensity': intensity,
                        'effort': effort,
                        'volume': volume,
                        'working_weight': weight,
                        'weight': weight,
                    })

                calculated_exercise = {
                    'exercise_id': exercise['exercise_id'],
                    'sets': calculated_sets,
                }
                calculated_schedule[label].append(calculated_exercise)

                if compute.generate_workouts and workout_entity is not None:
                    instance_ex = ExerciseInstance(
                        workout_id=workout_entity.id,
                        exercise_list_id=exercise['exercise_id'],
                        user_max_id=user_max.id,
                        sets=[
                            {
                                'id': idx + 1,
                                'weight': s.get('weight'),
                                'reps': s.get('volume'),
                                'rpe': s.get('effort'),
                                'volume': s.get('volume'),
                                'intensity': s.get('intensity'),
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
            next_w = self.db.query(Workout) \
                .filter(Workout.applied_plan_id == applied_plan.id) \
                .filter(Workout.completed_at.is_(None)) \
                .order_by(Workout.plan_order_index.asc()) \
                .first()
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
                id=(base_plan.id if base_plan else calendar_plan_id),
                name=(base_plan.name if base_plan else instance.name),
                schedule=calculated_schedule,
                duration_weeks=instance.duration_weeks,
                is_active=(base_plan.is_active if base_plan else True),
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
            next_workout=next_summary,
        )

        return applied_plan_response

    def get_user_applied_plans(self) -> list[AppliedCalendarPlanResponse]:
        """Получение всех примененных планов пользователя"""
        applied_plans = self.db.query(AppliedCalendarPlan)\
            .options(joinedload(AppliedCalendarPlan.calendar_plan))\
            .options(joinedload(AppliedCalendarPlan.user_maxes))\
            .order_by(AppliedCalendarPlan.start_date.desc())\
            .all()
        
        result: list[AppliedCalendarPlanResponse] = []
        for plan in applied_plans:
            # compute next workout summary for each plan
            next_summary = None
            next_w = self.db.query(Workout) \
                .filter(Workout.applied_plan_id == plan.id) \
                .filter(Workout.completed_at.is_(None)) \
                .order_by(Workout.plan_order_index.asc()) \
                .first()
            if next_w:
                next_summary = AppliedCalendarPlanResponse.NextWorkoutSummary(
                    id=next_w.id,
                    name=next_w.name,
                    scheduled_for=next_w.scheduled_for,
                    plan_order_index=next_w.plan_order_index,
                )

            result.append(
                AppliedCalendarPlanResponse(
                    id=plan.id,
                    calendar_plan_id=plan.calendar_plan_id,
                    start_date=plan.start_date,
                    end_date=plan.end_date,
                    is_active=plan.is_active,
                    calendar_plan=CalendarPlanResponse(
                        id=plan.calendar_plan.id,
                        name=plan.calendar_plan.name,
                        schedule=plan.calendar_plan.schedule,
                        duration_weeks=plan.calendar_plan.duration_weeks,
                        is_active=plan.calendar_plan.is_active
                    ),
                    user_maxes=[
                        UserMaxResponse(
                            id=um.id,
                            exercise_id=um.exercise_id,
                            max_weight=um.max_weight,
                            rep_max=um.rep_max
                        )
                        for um in plan.user_maxes
                    ],
                    next_workout=next_summary,
                )
            )

        return result

    def get_active_plan(self) -> Optional[AppliedCalendarPlanResponse]:
        """Получение активного плана пользователя"""
        active_plan = self.db.query(AppliedCalendarPlan)\
            .options(joinedload(AppliedCalendarPlan.calendar_plan))\
            .options(joinedload(AppliedCalendarPlan.user_maxes))\
            .filter(
                AppliedCalendarPlan.is_active == True
            )\
            .order_by(AppliedCalendarPlan.start_date.desc())\
            .first()
        
        if active_plan:
            # compute next workout summary for the active plan
            next_w = self.db.query(Workout) \
                .filter(Workout.applied_plan_id == active_plan.id) \
                .filter(Workout.completed_at.is_(None)) \
                .order_by(Workout.plan_order_index.asc()) \
                .first()
            next_summary = None
            if next_w:
                next_summary = AppliedCalendarPlanResponse.NextWorkoutSummary(
                    id=next_w.id,
                    name=next_w.name,
                    scheduled_for=next_w.scheduled_for,
                    plan_order_index=next_w.plan_order_index,
                )

            return AppliedCalendarPlanResponse(
                id=active_plan.id,
                calendar_plan_id=active_plan.calendar_plan_id,
                start_date=active_plan.start_date,
                end_date=active_plan.end_date,
                is_active=active_plan.is_active,
                calendar_plan=CalendarPlanResponse(
                    id=active_plan.calendar_plan.id,
                    name=active_plan.calendar_plan.name,
                    schedule=active_plan.calendar_plan.schedule,
                    duration_weeks=active_plan.calendar_plan.duration_weeks,
                    is_active=active_plan.calendar_plan.is_active
                ),
                user_maxes=[
                    UserMaxResponse(
                        id=um.id,
                        exercise_id=um.exercise_id,
                        max_weight=um.max_weight,
                        rep_max=um.rep_max
                    )
                    for um in active_plan.user_maxes
                ],
                next_workout=next_summary,
            )
        return None
