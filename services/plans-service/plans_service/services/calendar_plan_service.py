from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
import json
from sqlalchemy.orm import Session
from sqlalchemy import and_
from ..models.calendar import CalendarPlan, FavoriteCalendarPlan
from ..schemas.calendar_plan import CalendarPlanCreate, CalendarPlanUpdate, CalendarPlanResponse
from ..workout_calculation import WorkoutCalculator
from ..models.exercises import ExerciseList

class CalendarPlanService:
    def __init__(self, db: Session):
        self.db = db

    def create_plan(self, plan_data: CalendarPlanCreate) -> CalendarPlanResponse:
        """Создание нового календарного плана"""
        # Проверяем существование упражнений
        exercise_ids = set()
        for day in plan_data.schedule.values():
            for exercise in day:
                exercise_ids.add(exercise.exercise_id)
                
        existing_exercises = self.db.query(ExerciseList).filter(ExerciseList.id.in_(exercise_ids)).all()
        existing_exercise_ids = {e.id for e in existing_exercises}
        
        if not exercise_ids.issubset(existing_exercise_ids):
            missing_ids = exercise_ids - existing_exercise_ids
            raise ValueError(f"Упражнения с ID {missing_ids} не найдены")

        # Создаем базовый план
        plan = CalendarPlan(**plan_data.model_dump())
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        
        return self._get_plan_response(plan)

    def get_plan(self, plan_id: int) -> Optional[CalendarPlanResponse]:
        """Получение плана по ID"""
        plan = self.db.get(CalendarPlan, plan_id)
        if plan:
            return self._get_plan_response(plan)
        return None

    def get_all_plans(self) -> List[CalendarPlanResponse]:
        """Получение всех планов"""
        plans = self.db.query(CalendarPlan).all()
        return [self._get_plan_response(plan) for plan in plans]

    def generate_workouts(self, plan_id: int) -> List[Dict[str, Any]]:
        """Генерация тренировок на основе плана"""
        plan = self.db.get(CalendarPlan, plan_id)
        if not plan:
            return []

        workouts = []
        # Placeholder - generate workouts if needed in the future
        return workouts

    def update_plan(self, plan_id: int, plan_data: CalendarPlanUpdate) -> CalendarPlanResponse:
        """Обновление плана"""
        plan = self.db.get(CalendarPlan, plan_id)
        if not plan:
            raise ValueError("Plan not found")

        # Обновляем только переданные поля
        for field, value in plan_data.model_dump(exclude_none=True).items():
            setattr(plan, field, value)

        self.db.commit()
        return self._get_plan_response(plan)

    def delete_plan(self, plan_id: int) -> None:
        """Удаление плана"""
        plan = self.db.get(CalendarPlan, plan_id)
        if plan:
            plan.is_active = False
            self.db.commit()

    # Favorites API (global, без привязки к пользователю)
    def add_favorite(self, plan_id: int) -> CalendarPlanResponse:
        """Добавить план в избранные (глобально). Возвращает план."""
        plan = self.db.get(CalendarPlan, plan_id)
        if not plan:
            raise ValueError("Plan not found")
        exists = self.db.query(FavoriteCalendarPlan).filter(FavoriteCalendarPlan.calendar_plan_id == plan_id).first()
        if not exists:
            fav = FavoriteCalendarPlan(calendar_plan_id=plan_id)
            self.db.add(fav)
            self.db.commit()
        # Возвращаем актуальное состояние плана
        return self._get_plan_response(plan)

    def remove_favorite(self, plan_id: int) -> None:
        """Убрать план из избранных (глобально)."""
        fav = self.db.query(FavoriteCalendarPlan).filter(FavoriteCalendarPlan.calendar_plan_id == plan_id).first()
        if fav:
            self.db.delete(fav)
            self.db.commit()

    def get_favorite_plans(self) -> List[CalendarPlanResponse]:
        """Получить список избранных планов (глобально)."""
        favs = self.db.query(FavoriteCalendarPlan).all()
        plan_ids = [f.calendar_plan_id for f in favs]
        if not plan_ids:
            return []
        plans = self.db.query(CalendarPlan).filter(CalendarPlan.id.in_(plan_ids)).all()
        # Сохраняем порядок по дате добавления (опционально)
        plan_by_id = {p.id: p for p in plans}
        ordered = [plan_by_id[pid] for pid in plan_ids if pid in plan_by_id]
        return [self._get_plan_response(p) for p in ordered]

    def _get_plan_response(self, plan: CalendarPlan) -> CalendarPlanResponse:
        """Конвертация модели в схему ответа"""
        # Рассчитываем параметры для основного расписания
        calculated_schedule = {}
        schedule_raw = plan.schedule or {}
        # В некоторых БД миграциях поле могло сохраниться как TEXT
        # Парсим строковый JSON, если необходимо
        if isinstance(schedule_raw, str):
            try:
                schedule_data = json.loads(schedule_raw)
            except Exception:
                schedule_data = {}
        else:
            schedule_data = schedule_raw
        for day, exercises in schedule_data.items():
            # Игнорируем некорректные записи (не список упражнений)
            if not isinstance(exercises, list):
                continue
            calculated_schedule[day] = []
            for exercise in exercises:
                # Пропускаем элементы, которые не являются корректными описаниями упражнения
                if not isinstance(exercise, dict):
                    continue
                exercise_id = exercise.get('exercise_id')
                sets_list = exercise.get('sets') or []
                if exercise_id is None or not isinstance(sets_list, list):
                    # например, если случайно попали объекты мезоциклов и т.п.
                    continue
                sets = []
                for set_data in sets_list:
                    if not isinstance(set_data, dict):
                        continue
                    # Рассчитываем все возможные параметры сета
                    intensity = set_data.get('intensity')
                    effort = set_data.get('effort')
                    volume = set_data.get('volume')
                    working_weight = set_data.get('working_weight')
                    
                    calculated_volume = volume
                    calculated_intensity = intensity
                    calculated_effort = effort
                    
                    # Если есть intensity и effort, считаем volume
                    if intensity is not None and effort is not None:
                        calculated_volume = WorkoutCalculator.get_volume(
                            intensity=intensity,
                            effort=effort
                        )
                    # Если есть volume и effort, считаем intensity
                    elif volume is not None and effort is not None:
                        calculated_intensity = WorkoutCalculator.get_intensity(
                            volume=volume,
                            effort=effort
                        )
                    # Если есть volume и intensity, считаем effort
                    elif volume is not None and intensity is not None:
                        calculated_effort = WorkoutCalculator.get_effort(
                            volume=volume,
                            intensity=intensity
                        )

                    # Only include the calculated values, exclude working_weight as it's for workout instances only
                    calculated_set = {
                        'intensity': calculated_intensity,
                        'volume': calculated_volume,
                        'effort': calculated_effort
                    }
                    sets.append(calculated_set)
                calculated_exercise = {
                    'exercise_id': exercise_id,
                    'sets': sets
                }
                calculated_schedule[day].append(calculated_exercise)

        # Строим иерархию мезо/микроциклов, если она есть у плана
        mesocycles_resp = []
        try:
            for meso in (getattr(plan, 'mesocycles', None) or []):
                microcycles_resp = []
                for micro in (meso.microcycles or []):
                    mc_schedule = {}
                    mc_schedule_raw = micro.schedule or {}
                    if isinstance(mc_schedule_raw, str):
                        try:
                            mc_schedule_data = json.loads(mc_schedule_raw)
                        except Exception:
                            mc_schedule_data = {}
                    else:
                        mc_schedule_data = mc_schedule_raw
                    for day, exercises in mc_schedule_data.items():
                        if not isinstance(exercises, list):
                            continue
                        mc_schedule[day] = []
                        for exercise in exercises:
                            if not isinstance(exercise, dict):
                                continue
                            exercise_id = exercise.get('exercise_id')
                            sets_list = exercise.get('sets') or []
                            if exercise_id is None or not isinstance(sets_list, list):
                                continue
                            sets = []
                            for set_data in sets_list:
                                if not isinstance(set_data, dict):
                                    continue
                                intensity = set_data.get('intensity')
                                effort = set_data.get('effort')
                                volume = set_data.get('volume')
                                # working_weight is ignored in plan schema
                                calculated_volume = volume
                                calculated_intensity = intensity
                                calculated_effort = effort
                                if intensity is not None and effort is not None:
                                    calculated_volume = WorkoutCalculator.get_volume(
                                        intensity=intensity,
                                        effort=effort
                                    )
                                elif volume is not None and effort is not None:
                                    calculated_intensity = WorkoutCalculator.get_intensity(
                                        volume=volume,
                                        effort=effort
                                    )
                                elif volume is not None and intensity is not None:
                                    calculated_effort = WorkoutCalculator.get_effort(
                                        volume=volume,
                                        intensity=intensity
                                    )
                                sets.append({
                                    'intensity': calculated_intensity,
                                    'volume': calculated_volume,
                                    'effort': calculated_effort,
                                })
                            mc_schedule[day].append({
                                'exercise_id': exercise_id,
                                'sets': sets,
                            })
                    microcycles_resp.append({
                        'id': micro.id,
                        'mesocycle_id': micro.mesocycle_id,
                        'name': micro.name,
                        'notes': micro.notes,
                        'order_index': micro.order_index,
                        'schedule': mc_schedule,
                        'normalization_value': micro.normalization_value,
                        'normalization_unit': micro.normalization_unit,
                        'days_count': micro.days_count,
                    })
                mesocycles_resp.append({
                    'id': meso.id,
                    'name': meso.name,
                    'notes': meso.notes,
                    'order_index': meso.order_index,
                    'normalization_value': meso.normalization_value,
                    'normalization_unit': meso.normalization_unit,
                    'weeks_count': meso.weeks_count,
                    'microcycle_length_days': meso.microcycle_length_days,
                    'microcycles': microcycles_resp,
                })
        except Exception:
            # В случае проблем с загрузкой отношений или некорректных данных — вернем пустой список,
            # чтобы не ломать выдачу базового плана
            mesocycles_resp = []

        # Определяем признак избранного
        try:
            fav_exists = self.db.query(FavoriteCalendarPlan).filter(FavoriteCalendarPlan.calendar_plan_id == plan.id).first() is not None
        except Exception:
            fav_exists = False

        return CalendarPlanResponse(
            id=plan.id,
            name=plan.name,
            schedule=calculated_schedule,
            duration_weeks=plan.duration_weeks,
            is_active=plan.is_active,
            mesocycles=mesocycles_resp,
            is_favorite=fav_exists,
        )
