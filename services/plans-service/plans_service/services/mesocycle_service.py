from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from ..models.calendar import (
    CalendarPlan,
    Mesocycle,
    Microcycle,
    PlanExercise,
    PlanSet,
    PlanWorkout,
)
from ..schemas.mesocycle import (
    MesocycleCreate,
    MesocycleResponse,
    MesocycleUpdate,
    MicrocycleCreate,
    MicrocycleResponse,
    MicrocycleUpdate,
)


class MesocycleService:
    def __init__(self, db: AsyncSession, user_id: str):
        self.db = db
        self.user_id = user_id

    def _require_user_id(self) -> str:
        if not self.user_id:
            raise ValueError("User context required")
        return self.user_id

    async def _check_plan_permission(self, plan_id: int) -> CalendarPlan:
        user_id = self._require_user_id()
        stmt = select(CalendarPlan).where(CalendarPlan.id == plan_id, CalendarPlan.user_id == user_id)
        result = await self.db.execute(stmt)
        plan = result.scalars().first()
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found or permission denied")
        return plan

    async def _check_mesocycle_permission(self, mesocycle_id: int) -> Optional[Mesocycle]:
        user_id = self._require_user_id()
        stmt = (
            select(Mesocycle)
            .options(joinedload(Mesocycle.calendar_plan))
            .join(Mesocycle.calendar_plan)
            .where(Mesocycle.id == mesocycle_id, CalendarPlan.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        meso = result.scalars().first()
        if not meso:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mesocycle not found")
        return meso

    async def _check_microcycle_permission(self, microcycle_id: int) -> Microcycle:
        user_id = self._require_user_id()
        stmt = (
            select(Microcycle)
            .options(joinedload(Microcycle.mesocycle).joinedload(Mesocycle.calendar_plan))
            .join(Microcycle.mesocycle)
            .join(Mesocycle.calendar_plan)
            .where(Microcycle.id == microcycle_id, CalendarPlan.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        micro = result.scalars().first()
        if not micro:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Microcycle not found")
        return micro

    async def _serialize_schedule(self, schedule: Optional[Dict[str, List[Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        if not schedule:
            return {}
        serialized: Dict[str, List[Dict[str, Any]]] = {}
        for day, items in schedule.items():
            day_items: List[Dict[str, Any]] = []
            for it in items or []:
                try:
                    dumped = it.model_dump()
                except AttributeError:
                    dumped = dict(it)
                day_items.append(dumped)
            serialized[day] = day_items
        return serialized

    async def list_mesocycles(self, plan_id: int) -> List[MesocycleResponse]:
        try:
            await self._check_plan_permission(plan_id)
            user_id = self._require_user_id()
            stmt = (
                select(Mesocycle)
                .join(Mesocycle.calendar_plan)
                .where(
                    Mesocycle.calendar_plan_id == plan_id,
                    CalendarPlan.user_id == user_id,
                )
                .order_by(Mesocycle.order_index.asc(), Mesocycle.id.asc())
            )
            result = await self.db.execute(stmt)
            meso = result.scalars().all()
            return [MesocycleResponse.model_validate(m) for m in meso]
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list mesocycles: {str(e)}",
            )

    async def create_mesocycle(self, data: MesocycleCreate) -> MesocycleResponse:
        try:
            await self._check_plan_permission(data.calendar_plan_id)
            user_id = self._require_user_id()
            order_index = data.order_index if (data.order_index is not None and data.order_index > 0) else None
            if order_index is None:
                stmt = (
                    select(Mesocycle)
                    .join(Mesocycle.calendar_plan)
                    .where(
                        Mesocycle.calendar_plan_id == data.calendar_plan_id,
                        CalendarPlan.user_id == user_id,
                    )
                    .order_by(Mesocycle.order_index.desc(), Mesocycle.id.desc())
                )
                result = await self.db.execute(stmt)
                last = result.scalars().first()
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
            await self.db.commit()
            await self.db.refresh(m)
            return MesocycleResponse.model_validate(m)
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create mesocycle: {str(e)}",
            )

    async def update_mesocycle(self, mesocycle_id: int, data: MesocycleUpdate) -> MesocycleResponse:
        m = await self._check_mesocycle_permission(mesocycle_id)
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
        await self.db.commit()
        await self.db.refresh(m)
        return MesocycleResponse.model_validate(m)

    async def delete_mesocycle(self, mesocycle_id: int) -> None:
        m = await self._check_mesocycle_permission(mesocycle_id)
        await self.db.delete(m)
        await self.db.commit()

    async def get_mesocycle_by_id(self, mesocycle_id: int) -> Optional[Mesocycle]:
        await self._check_mesocycle_permission(mesocycle_id)
        stmt = select(Mesocycle).options(selectinload(Mesocycle.microcycles)).where(Mesocycle.id == mesocycle_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_microcycles(self, mesocycle_id: int) -> List[MicrocycleResponse]:
        await self._check_mesocycle_permission(mesocycle_id)
        stmt = (
            select(Microcycle)
            .join(Microcycle.mesocycle)
            .join(Mesocycle.calendar_plan)
            .where(
                Microcycle.mesocycle_id == mesocycle_id,
                CalendarPlan.user_id == self._require_user_id(),
            )
            .order_by(Microcycle.order_index.asc(), Microcycle.id.asc())
        )
        result = await self.db.execute(stmt)
        micro = result.scalars().all()
        return [MicrocycleResponse.model_validate(mc) for mc in micro]

    async def create_microcycle(self, data: MicrocycleCreate) -> MicrocycleResponse:
        meso = await self._check_mesocycle_permission(data.mesocycle_id)
        if not meso:
            raise HTTPException(status_code=404, detail="Mesocycle not found")
        try:
            order_index = data.order_index if (data.order_index is not None and data.order_index > 0) else None
            if order_index is None:
                stmt = (
                    select(Microcycle)
                    .join(Microcycle.mesocycle)
                    .join(Mesocycle.calendar_plan)
                    .where(
                        Microcycle.mesocycle_id == data.mesocycle_id,
                        CalendarPlan.user_id == self._require_user_id(),
                    )
                    .order_by(Microcycle.order_index.desc(), Microcycle.id.desc())
                )
                result = await self.db.execute(stmt)
                last = result.scalars().first()
                order_index = (last.order_index if last else 0) + 1

            mc = Microcycle(
                mesocycle_id=data.mesocycle_id,
                name=data.name,
                notes=data.notes,
                order_index=order_index,
                schedule=await self._serialize_schedule(data.schedule),
                normalization_value=data.normalization_value,
                normalization_unit=(data.normalization_unit if data.normalization_unit is not None else None),
                normalization_rules=[rule.model_dump() for rule in (data.normalization_rules or [])] or None,
                days_count=data.days_count,
            )
            self.db.add(mc)
            await self.db.commit()
            await self.db.refresh(mc)
            return MicrocycleResponse.model_validate(mc)
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create microcycle: {str(e)}",
            )

    async def update_microcycle(self, microcycle_id: int, data: MicrocycleUpdate) -> MicrocycleResponse:
        mc = await self._check_microcycle_permission(microcycle_id)
        if data.name is not None:
            mc.name = data.name
        if data.notes is not None:
            mc.notes = data.notes
        if data.order_index is not None:
            mc.order_index = data.order_index
        # Apply schedule into relational structure (plan_workouts/exercises/sets)
        if data.schedule is not None:
            # Eager-load existing workouts/exercises/sets to avoid async lazy-load (MissingGreenlet)
            stmt_pw = (
                select(PlanWorkout)
                .options(selectinload(PlanWorkout.exercises).selectinload(PlanExercise.sets))
                .where(PlanWorkout.microcycle_id == mc.id)
            )
            result_pw = await self.db.execute(stmt_pw)
            existing_workouts = list(result_pw.scalars().all())

            # Build lookup existing workouts by day index (1-based) and by label
            existing_by_day: dict[int, PlanWorkout] = {}
            for pw in existing_workouts:
                # Try parse "Day X" to int, else fallback to order_index + 1
                day_idx: Optional[int] = None
                label = (pw.day_label or "").strip().lower()
                if label.startswith("day "):
                    try:
                        day_idx = int(label[4:].strip())
                    except Exception:
                        day_idx = None
                if day_idx is None:
                    day_idx = (pw.order_index or 0) + 1
                existing_by_day[day_idx] = pw

            # Iterate incoming schedule per day
            for raw_day, items in (data.schedule or {}).items():
                # Accept keys like "1" or "Day 1"
                day_idx: int | None = None
                try:
                    day_idx = int(str(raw_day).strip().split()[-1])
                except Exception:
                    day_idx = None
                if day_idx is None or day_idx < 1:
                    # Skip invalid keys
                    continue

                pw = existing_by_day.get(day_idx)
                if pw is None:
                    # Create a new workout for this day
                    pw = PlanWorkout(
                        microcycle_id=mc.id,
                        day_label=f"Day {day_idx}",
                        order_index=day_idx - 1,
                    )
                    self.db.add(pw)
                    await self.db.flush()
                    existing_by_day[day_idx] = pw

                # Replace exercises for this day
                new_exercises: list[PlanExercise] = []
                for item in items or []:
                    if not isinstance(item, dict):
                        continue
                    ex_id = item.get("exercise_id") or item.get("exercise_list_id")
                    try:
                        ex_id = int(ex_id) if ex_id is not None else None
                    except Exception:
                        ex_id = None
                    if ex_id is None:
                        continue
                    name = item.get("name") or ""
                    sets_payload = item.get("sets") or []
                    new_sets: list[PlanSet] = []
                    for s in sets_payload:
                        if not isinstance(s, dict):
                            continue
                        new_sets.append(
                            PlanSet(
                                order_index=len(new_sets),
                                intensity=s.get("intensity"),
                                effort=s.get("effort"),
                                volume=s.get("volume"),
                                working_weight=s.get("working_weight"),
                            )
                        )
                    new_exercises.append(
                        PlanExercise(
                            plan_workout_id=pw.id,
                            exercise_definition_id=ex_id,
                            exercise_name=name,
                            order_index=len(new_exercises),
                            sets=new_sets,
                        )
                    )

                # Assign, old ones are deleted via cascade orphan
                pw.exercises = new_exercises
        if data.normalization_value is not None:
            mc.normalization_value = data.normalization_value
        if data.normalization_unit is not None:
            mc.normalization_unit = data.normalization_unit
        if data.normalization_rules is not None:
            mc.normalization_rules = [rule.model_dump() for rule in (data.normalization_rules or [])] or None
        if data.days_count is not None:
            mc.days_count = data.days_count
        await self.db.commit()
        await self.db.refresh(mc)
        return MicrocycleResponse.model_validate(mc)

    async def delete_microcycle(self, microcycle_id: int) -> None:
        mc = await self._check_microcycle_permission(microcycle_id)
        await self.db.delete(mc)
        await self.db.commit()

    async def get_microcycle_by_id(self, microcycle_id: int) -> Optional[Microcycle]:
        await self._check_microcycle_permission(microcycle_id)
        stmt = (
            select(Microcycle)
            .options(
                selectinload(Microcycle.plan_workouts)
                .selectinload(PlanWorkout.exercises)
                .selectinload(PlanExercise.sets)
            )
            .where(Microcycle.id == microcycle_id)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()
