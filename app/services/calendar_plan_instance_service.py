from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import math
from app.models.calendar import CalendarPlan, CalendarPlanInstance
from app.schemas.calendar_plan import (
    CalendarPlanInstanceCreate,
    CalendarPlanInstanceUpdate,
    CalendarPlanInstanceResponse,
)

class CalendarPlanInstanceService:
    def __init__(self, db: Session):
        self.db = db

    def list_instances(self) -> List[CalendarPlanInstanceResponse]:
        inst = self.db.query(CalendarPlanInstance).all()
        return [self._to_response(i) for i in inst]

    def get_instance(self, instance_id: int) -> Optional[CalendarPlanInstanceResponse]:
        inst = self.db.get(CalendarPlanInstance, instance_id)
        return self._to_response(inst) if inst else None

    def delete_instance(self, instance_id: int) -> None:
        inst = self.db.get(CalendarPlanInstance, instance_id)
        if inst:
            self.db.delete(inst)
            self.db.commit()

    def create_from_plan(self, plan_id: int) -> CalendarPlanInstanceResponse:
        plan = self.db.get(CalendarPlan, plan_id)
        if not plan:
            raise ValueError("Plan not found")

        # If legacy top-level schedule is provided, keep backward compatibility
        if plan.schedule:
            schedule_with_ids = self._index_schedule(plan.schedule)
            duration_weeks = plan.duration_weeks
        else:
            # New hierarchical structure: concatenate all microcycles in order into a flat schedule
            flat_schedule: Dict[str, List[Dict[str, Any]]] = {}
            day_counter = 0
            total_days = 0
            try:
                mesocycles = sorted(list(plan.mesocycles or []), key=lambda m: (m.order_index, m.id))
                for m in mesocycles:
                    microcycles = sorted(list(m.microcycles or []), key=lambda mc: (mc.order_index, mc.id))
                    for mc in microcycles:
                        mc_sched = mc.schedule or {}
                        # Order microcycle days by numeric suffix of keys like 'day1', 'day2', ...
                        def _day_key(dk: str) -> int:
                            try:
                                return int(str(dk).lower().replace('day', ''))
                            except Exception:
                                return 0
                        for _, items in sorted(mc_sched.items(), key=lambda kv: _day_key(kv[0])):
                            day_counter += 1
                            flat_schedule[f'day{day_counter}'] = items or []
                total_days = day_counter
            except Exception:
                # If anything goes wrong, keep empty schedule; client can still edit later
                flat_schedule = {}
                total_days = 0

            # Normalize and index sets/items
            schedule_with_ids = self._index_schedule(flat_schedule)
            # Preserve full plan duration if available; else derive from total_days
            if plan.duration_weeks:
                duration_weeks = max(1, plan.duration_weeks)
            else:
                duration_weeks = max(1, math.ceil((total_days or 1) / 7))

        inst = CalendarPlanInstance(
            source_plan_id=plan.id,
            name=plan.name,
            schedule=schedule_with_ids,
            duration_weeks=duration_weeks,
        )
        self.db.add(inst)
        self.db.commit()
        self.db.refresh(inst)
        return self._to_response(inst)

    def create(self, data: CalendarPlanInstanceCreate) -> CalendarPlanInstanceResponse:
        schedule = data.schedule
        # trust incoming ids; otherwise index if empty
        if not schedule:
            schedule = {}
        else:
            # Convert Pydantic objects into plain JSON-serializable dicts
            schedule = self._dump_schedule(schedule)
        inst = CalendarPlanInstance(
            source_plan_id=data.source_plan_id,
            name=data.name,
            schedule=schedule,
            duration_weeks=data.duration_weeks,
        )
        self.db.add(inst)
        self.db.commit()
        self.db.refresh(inst)
        return self._to_response(inst)

    def update(self, instance_id: int, data: CalendarPlanInstanceUpdate) -> CalendarPlanInstanceResponse:
        inst = self.db.get(CalendarPlanInstance, instance_id)
        if not inst:
            raise ValueError("Instance not found")
        if data.name is not None:
            inst.name = data.name
        if data.duration_weeks is not None:
            inst.duration_weeks = data.duration_weeks
        if data.schedule is not None:
            # Convert Pydantic objects into plain JSON-serializable dicts
            inst.schedule = self._dump_schedule(data.schedule)
        self.db.commit()
        self.db.refresh(inst)
        return self._to_response(inst)

    def _index_schedule(self, schedule: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        """Add stable incremental ids for items and sets within each day.
        Also normalize set structure to dicts with keys: intensity, effort, volume.
        Some stored plans might keep sets as positional arrays like [intensity, effort, volume].
        """
        result: Dict[str, List[Dict[str, Any]]] = {}
        for day, items in (schedule or {}).items():
            new_items = []
            for i, item in enumerate(items or [], start=1):
                sets = item.get('sets', []) or []
                new_sets = []
                for j, s in enumerate(sets, start=1):
                    intensity = None
                    effort = None
                    volume = None
                    # Normalize various possible shapes
                    if isinstance(s, dict):
                        intensity = s.get('intensity')
                        effort = s.get('effort')
                        volume = s.get('volume')
                    elif isinstance(s, (list, tuple)):
                        # Positional: [intensity, effort, volume]
                        if len(s) > 0: intensity = s[0]
                        if len(s) > 1: effort = s[1]
                        if len(s) > 2: volume = s[2]
                    else:
                        # Unknown shape; keep as None
                        pass

                    ns = {
                        'id': j,
                        'intensity': intensity,
                        'effort': effort,
                        'volume': volume,
                    }
                    new_sets.append(ns)
                ni = {
                    'id': i,
                    'exercise_id': item.get('exercise_id'),
                    'sets': new_sets,
                }
                new_items.append(ni)
            result[day] = new_items
        return result

    def _dump_schedule(self, schedule: Dict[str, List[Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Convert a schedule possibly containing Pydantic models into a plain JSON-serializable dict.
        Accepts Dict[str, List[ExerciseScheduleItemInstance]] and returns Dict[str, List[dict]].
        """
        dumped: Dict[str, List[Dict[str, Any]]] = {}
        for day, items in (schedule or {}).items():
            dumped_items: List[Dict[str, Any]] = []
            for item in items or []:
                # Pydantic item may have .model_dump(); if it's already dict, keep it
                if hasattr(item, 'model_dump'):
                    item_dict = item.model_dump()
                elif isinstance(item, dict):
                    item_dict = item
                else:
                    # Fallback: best-effort extraction
                    item_dict = {
                        'id': getattr(item, 'id', None),
                        'exercise_id': getattr(item, 'exercise_id', None),
                        'sets': getattr(item, 'sets', []),
                    }
                # Ensure sets are plain dicts
                sets = []
                for s in item_dict.get('sets', []) or []:
                    if hasattr(s, 'model_dump'):
                        sets.append(s.model_dump())
                    elif isinstance(s, dict):
                        sets.append(s)
                    else:
                        sets.append({
                            'id': getattr(s, 'id', None),
                            'intensity': getattr(s, 'intensity', None),
                            'effort': getattr(s, 'effort', None),
                            'volume': getattr(s, 'volume', None),
                        })
                item_dict['sets'] = sets
                dumped_items.append(item_dict)
            dumped[day] = dumped_items
        return dumped

    def _to_response(self, inst: CalendarPlanInstance) -> CalendarPlanInstanceResponse:
        return CalendarPlanInstanceResponse(
            id=inst.id,
            source_plan_id=inst.source_plan_id,
            name=inst.name,
            schedule=inst.schedule,  # already indexed
            duration_weeks=inst.duration_weeks,
        )
