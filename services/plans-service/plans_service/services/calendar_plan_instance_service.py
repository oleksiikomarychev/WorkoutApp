import math
from typing import Any

from sqlalchemy.orm import Session

from ..models.calendar import CalendarPlan, CalendarPlanInstance
from ..schemas.calendar_plan import (
    CalendarPlanInstanceCreate,
    CalendarPlanInstanceResponse,
    CalendarPlanInstanceUpdate,
)


class CalendarPlanInstanceService:
    def __init__(self, db: Session, user_id: str | None = None):
        self.db = db
        self.user_id = user_id

    def _require_user_id(self) -> str:
        if not self.user_id:
            raise ValueError("User context required")
        return self.user_id

    def list_instances(self) -> list[CalendarPlanInstanceResponse]:
        user_id = self._require_user_id()
        instances = (
            self.db.query(CalendarPlanInstance)
            .join(CalendarPlan, CalendarPlan.id == CalendarPlanInstance.source_plan_id)
            .filter(CalendarPlan.user_id == user_id)
            .all()
        )
        return [self._to_response(i) for i in instances]

    def get_instance(self, instance_id: int) -> CalendarPlanInstanceResponse | None:
        user_id = self._require_user_id()
        inst = (
            self.db.query(CalendarPlanInstance)
            .join(CalendarPlan, CalendarPlan.id == CalendarPlanInstance.source_plan_id)
            .filter(
                CalendarPlanInstance.id == instance_id,
                CalendarPlan.user_id == user_id,
            )
            .first()
        )
        return self._to_response(inst) if inst else None

    def delete_instance(self, instance_id: int) -> None:
        user_id = self._require_user_id()
        inst = (
            self.db.query(CalendarPlanInstance)
            .join(CalendarPlan, CalendarPlan.id == CalendarPlanInstance.source_plan_id)
            .filter(
                CalendarPlanInstance.id == instance_id,
                CalendarPlan.user_id == user_id,
            )
            .first()
        )
        if inst:
            self.db.delete(inst)
            self.db.commit()

    def create_from_plan(self, plan_id: int) -> CalendarPlanInstanceResponse:
        try:
            user_id = self._require_user_id()

            plan = (
                self.db.query(CalendarPlan)
                .filter(
                    CalendarPlan.id == plan_id,
                    CalendarPlan.user_id == user_id,
                )
                .first()
            )
            if not plan:
                raise ValueError("Plan not found or permission denied")

            if plan.schedule:
                schedule_with_ids = self._index_schedule(plan.schedule)
                duration_weeks = plan.duration_weeks
            else:
                flat_schedule: dict[str, list[dict[str, Any]]] = {}
                day_counter = 0
                total_days = 0
                try:
                    mesocycles = sorted(list(plan.mesocycles or []), key=lambda m: (m.order_index, m.id))
                    for m in mesocycles:
                        microcycles = sorted(
                            list(m.microcycles or []),
                            key=lambda mc: (mc.order_index, mc.id),
                        )
                        for mc in microcycles:
                            mc_sched = mc.schedule or {}

                            def _day_key(dk: str) -> int:
                                try:
                                    return int(str(dk).lower().replace("day", ""))
                                except ValueError:
                                    return 0

                            for _, items in sorted(mc_sched.items(), key=lambda kv: _day_key(kv[0])):
                                day_counter += 1
                                flat_schedule[f"day{day_counter}"] = items or []
                    total_days = day_counter
                except (TypeError, AttributeError):
                    # Fallback if mesocycle/microcycle structure is unexpected
                    flat_schedule = {}
                    total_days = 0

                schedule_with_ids = self._index_schedule(flat_schedule)

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
        except Exception:
            self.db.rollback()
            raise

    def create(self, data: CalendarPlanInstanceCreate) -> CalendarPlanInstanceResponse:
        try:
            user_id = self._require_user_id()
            schedule = data.schedule

            if not schedule:
                schedule = {}
            else:
                schedule = self._dump_schedule(schedule)
            plan = (
                self.db.query(CalendarPlan)
                .filter(
                    CalendarPlan.id == data.source_plan_id,
                    CalendarPlan.user_id == user_id,
                )
                .first()
            )
            if not plan:
                raise ValueError("Plan not found or permission denied")

            inst = CalendarPlanInstance(
                source_plan_id=plan.id,
                name=data.name,
                schedule=schedule,
                duration_weeks=data.duration_weeks,
            )
            self.db.add(inst)
            self.db.commit()
            self.db.refresh(inst)
            return self._to_response(inst)
        except Exception:
            self.db.rollback()
            raise

    def update(self, instance_id: int, data: CalendarPlanInstanceUpdate) -> CalendarPlanInstanceResponse:
        try:
            user_id = self._require_user_id()
            inst = (
                self.db.query(CalendarPlanInstance)
                .join(CalendarPlan, CalendarPlan.id == CalendarPlanInstance.source_plan_id)
                .filter(
                    CalendarPlanInstance.id == instance_id,
                    CalendarPlan.user_id == user_id,
                )
                .first()
            )
            if not inst:
                raise ValueError("Instance not found")
            if data.name is not None:
                inst.name = data.name
            if data.duration_weeks is not None:
                inst.duration_weeks = data.duration_weeks
            if data.schedule is not None:
                inst.schedule = self._dump_schedule(data.schedule)
            self.db.commit()
            self.db.refresh(inst)
            return self._to_response(inst)
        except Exception:
            self.db.rollback()
            raise

    def _index_schedule(self, schedule: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
        result: dict[str, list[dict[str, Any]]] = {}
        for day, items in (schedule or {}).items():
            new_items = []
            for i, item in enumerate(items or [], start=1):
                sets = item.get("sets", []) or []
                new_sets = []
                for j, s in enumerate(sets, start=1):
                    intensity = None
                    effort = None
                    volume = None

                    if isinstance(s, dict):
                        intensity = s.get("intensity")
                        effort = s.get("effort")
                        volume = s.get("volume")
                    elif isinstance(s, list):
                        if len(s) > 0:
                            intensity = s[0]
                        if len(s) > 1:
                            effort = s[1]
                        if len(s) > 2:
                            volume = s[2]
                    else:
                        pass

                    ns = {
                        "id": j,
                        "intensity": intensity,
                        "effort": effort,
                        "volume": volume,
                    }
                    new_sets.append(ns)
                ni = {
                    "id": i,
                    "exercise_id": item.get("exercise_id"),
                    "sets": new_sets,
                }
                new_items.append(ni)
            result[day] = new_items
        return result

    def _dump_schedule(self, schedule: dict[str, list[Any]]) -> dict[str, list[dict[str, Any]]]:
        dumped: dict[str, list[dict[str, Any]]] = {}
        for day, items in (schedule or {}).items():
            dumped_items: list[dict[str, Any]] = []
            for item in items or []:
                if hasattr(item, "model_dump"):
                    item_dict = item.model_dump()
                elif isinstance(item, dict):
                    item_dict = item
                else:
                    item_dict = {
                        "id": getattr(item, "id", None),
                        "exercise_id": getattr(item, "exercise_id", None),
                        "sets": getattr(item, "sets", []),
                    }

                sets = []
                for s in item_dict.get("sets", []) or []:
                    if hasattr(s, "model_dump"):
                        sets.append(s.model_dump())
                    elif isinstance(s, dict):
                        sets.append(s)
                    else:
                        sets.append(
                            {
                                "id": getattr(s, "id", None),
                                "intensity": getattr(s, "intensity", None),
                                "effort": getattr(s, "effort", None),
                                "volume": getattr(s, "volume", None),
                            }
                        )
                item_dict["sets"] = sets
                dumped_items.append(item_dict)
            dumped[day] = dumped_items
        return dumped

    def _to_response(self, inst: CalendarPlanInstance) -> CalendarPlanInstanceResponse:
        return CalendarPlanInstanceResponse(
            id=inst.id,
            source_plan_id=inst.source_plan_id,
            name=inst.name,
            schedule=inst.schedule,
            duration_weeks=inst.duration_weeks,
        )
