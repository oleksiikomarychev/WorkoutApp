from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException

from app.models.calendar import CalendarPlan, Mesocycle, Microcycle
from app.schemas.mesocycle import (
    MesocycleCreate,
    MesocycleUpdate,
    MesocycleResponse,
    MicrocycleCreate,
    MicrocycleUpdate,
    MicrocycleResponse,
)


class MesocycleService:
    def __init__(self, db: Session):
        self.db = db

    # Internal: ensure schedule is JSON-serializable (list[ExerciseScheduleItem] -> list[dict])
    def _serialize_schedule(self, schedule: Optional[Dict[str, List[Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        if not schedule:
            return {}
        serialized: Dict[str, List[Dict[str, Any]]] = {}
        for day, items in schedule.items():
            # Each item can be a pydantic model (ExerciseScheduleItem) or already a dict
            day_items: List[Dict[str, Any]] = []
            for it in items or []:
                try:
                    # Prefer pydantic model_dump if available (will drop working_weight per schema override)
                    dumped = it.model_dump()  # type: ignore[attr-defined]
                except AttributeError:
                    # Assume it's already a plain dict
                    dumped = dict(it)
                day_items.append(dumped)
            serialized[day] = day_items
        return serialized

    # ===== Mesocycles =====
    def list_mesocycles(self, plan_id: int) -> List[MesocycleResponse]:
        plan = self.db.get(CalendarPlan, plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        meso = (
            self.db.query(Mesocycle)
            .filter(Mesocycle.calendar_plan_id == plan_id)
            .order_by(Mesocycle.order_index.asc(), Mesocycle.id.asc())
            .all()
        )
        return [MesocycleResponse.model_validate(m) for m in meso]

    def create_mesocycle(self, data: MesocycleCreate) -> MesocycleResponse:
        plan = self.db.get(CalendarPlan, data.calendar_plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        # Determine order_index: use provided (>0) or append to the end
        order_index = data.order_index if (data.order_index is not None and data.order_index > 0) else None
        if order_index is None:
            last = (
                self.db.query(Mesocycle)
                .filter(Mesocycle.calendar_plan_id == data.calendar_plan_id)
                .order_by(Mesocycle.order_index.desc(), Mesocycle.id.desc())
                .first()
            )
            order_index = (last.order_index if last else 0) + 1

        m = Mesocycle(
            calendar_plan_id=data.calendar_plan_id,
            name=data.name,
            notes=data.notes,
            order_index=order_index,
            normalization_value=data.normalization_value,
            normalization_unit=(data.normalization_unit if data.normalization_unit is not None else None),
            weeks_count=data.weeks_count,
            microcycle_length_days=data.microcycle_length_days,
        )
        self.db.add(m)
        self.db.commit()
        self.db.refresh(m)
        return MesocycleResponse.model_validate(m)

    def update_mesocycle(self, mesocycle_id: int, data: MesocycleUpdate) -> MesocycleResponse:
        m = self.db.get(Mesocycle, mesocycle_id)
        if not m:
            raise HTTPException(status_code=404, detail="Mesocycle not found")
        if data.name is not None:
            m.name = data.name
        if data.notes is not None:
            m.notes = data.notes
        if data.order_index is not None:
            m.order_index = data.order_index
        if data.normalization_value is not None:
            m.normalization_value = data.normalization_value
        if data.normalization_unit is not None:
            m.normalization_unit = data.normalization_unit
        if data.weeks_count is not None:
            m.weeks_count = data.weeks_count
        if data.microcycle_length_days is not None:
            m.microcycle_length_days = data.microcycle_length_days
        self.db.commit()
        self.db.refresh(m)
        return MesocycleResponse.model_validate(m)

    def delete_mesocycle(self, mesocycle_id: int) -> None:
        m = self.db.get(Mesocycle, mesocycle_id)
        if not m:
            raise HTTPException(status_code=404, detail="Mesocycle not found")
        self.db.delete(m)
        self.db.commit()

    # ===== Microcycles =====
    def list_microcycles(self, mesocycle_id: int) -> List[MicrocycleResponse]:
        meso = self.db.get(Mesocycle, mesocycle_id)
        if not meso:
            raise HTTPException(status_code=404, detail="Mesocycle not found")
        micro = (
            self.db.query(Microcycle)
            .filter(Microcycle.mesocycle_id == mesocycle_id)
            .order_by(Microcycle.order_index.asc(), Microcycle.id.asc())
            .all()
        )
        return [MicrocycleResponse.model_validate(mc) for mc in micro]

    def create_microcycle(self, data: MicrocycleCreate) -> MicrocycleResponse:
        meso = self.db.get(Mesocycle, data.mesocycle_id)
        if not meso:
            raise HTTPException(status_code=404, detail="Mesocycle not found")
        # Determine order_index: use provided (>0) or append to the end within mesocycle
        order_index = data.order_index if (data.order_index is not None and data.order_index > 0) else None
        if order_index is None:
            last = (
                self.db.query(Microcycle)
                .filter(Microcycle.mesocycle_id == data.mesocycle_id)
                .order_by(Microcycle.order_index.desc(), Microcycle.id.desc())
                .first()
            )
            order_index = (last.order_index if last else 0) + 1

        mc = Microcycle(
            mesocycle_id=data.mesocycle_id,
            name=data.name,
            notes=data.notes,
            order_index=order_index,
            schedule=self._serialize_schedule(data.schedule),
            normalization_value=data.normalization_value,
            normalization_unit=(data.normalization_unit if data.normalization_unit is not None else None),
            days_count=data.days_count,
        )
        self.db.add(mc)
        self.db.commit()
        self.db.refresh(mc)
        return MicrocycleResponse.model_validate(mc)

    def update_microcycle(self, microcycle_id: int, data: MicrocycleUpdate) -> MicrocycleResponse:
        mc = self.db.get(Microcycle, microcycle_id)
        if not mc:
            raise HTTPException(status_code=404, detail="Microcycle not found")
        if data.name is not None:
            mc.name = data.name
        if data.notes is not None:
            mc.notes = data.notes
        if data.order_index is not None:
            mc.order_index = data.order_index
        if data.schedule is not None:
            mc.schedule = self._serialize_schedule(data.schedule)
        if data.normalization_value is not None:
            mc.normalization_value = data.normalization_value
        if data.normalization_unit is not None:
            mc.normalization_unit = data.normalization_unit
        if data.days_count is not None:
            mc.days_count = data.days_count
        self.db.commit()
        self.db.refresh(mc)
        return MicrocycleResponse.model_validate(mc)

    def delete_microcycle(self, microcycle_id: int) -> None:
        mc = self.db.get(Microcycle, microcycle_id)
        if not mc:
            raise HTTPException(status_code=404, detail="Microcycle not found")
        self.db.delete(mc)
        self.db.commit()
