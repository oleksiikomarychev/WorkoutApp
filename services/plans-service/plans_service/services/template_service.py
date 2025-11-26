from __future__ import annotations

from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.calendar import (
    AppliedCalendarPlan,
    AppliedMesocycle,
    AppliedMicrocycle,
    AppliedWorkout,
    CalendarPlan,
    Mesocycle,
    Microcycle,
    PlanExercise,
    PlanSet,
    PlanWorkout,
)
from ..models.templates import MesocycleTemplate, MicrocycleTemplate
from ..schemas.templates import (
    InstantiateFromExistingRequest,
    InstantiateFromTemplateRequest,
    MesocycleTemplateCreate,
    MesocycleTemplateResponse,
    MesocycleTemplateUpdate,
    MicrocycleTemplateDto,
    PlacementMode,
)


class TemplateService:
    def __init__(self, db: AsyncSession, user_id: str):
        self.db = db
        self.user_id = user_id

    async def _require_plan(self, plan_id: int) -> CalendarPlan:
        stmt = select(CalendarPlan).where(CalendarPlan.id == plan_id, CalendarPlan.user_id == self.user_id)
        res = await self.db.execute(stmt)
        plan = res.scalars().first()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        return plan

    async def list_templates(self) -> List[MesocycleTemplateResponse]:
        stmt = (
            select(MesocycleTemplate)
            .where((MesocycleTemplate.user_id == self.user_id) | (MesocycleTemplate.is_public.is_(True)))
            .order_by(MesocycleTemplate.id.desc())
        )
        res = await self.db.execute(stmt)
        items = list(res.scalars().all())
        return [self._to_response(i) for i in items]

    async def get_template(self, template_id: int) -> MesocycleTemplateResponse:
        stmt = select(MesocycleTemplate).where(MesocycleTemplate.id == template_id)
        res = await self.db.execute(stmt)
        tpl = res.scalars().first()
        if not tpl or (not tpl.is_public and tpl.user_id != self.user_id):
            raise HTTPException(status_code=404, detail="Template not found")
        return self._to_response(tpl)

    async def create_template(self, payload: MesocycleTemplateCreate) -> MesocycleTemplateResponse:
        tpl = MesocycleTemplate(
            user_id=self.user_id,
            name=payload.name,
            notes=payload.notes,
            weeks_count=payload.weeks_count,
            microcycle_length_days=payload.microcycle_length_days,
            normalization_value=payload.normalization_value,
            normalization_unit=payload.normalization_unit,
            is_public=payload.is_public or False,
        )
        self.db.add(tpl)
        await self.db.flush()
        # microcycles
        for mc in payload.microcycles or []:
            self.db.add(
                MicrocycleTemplate(
                    mesocycle_template_id=tpl.id,
                    name=mc.name,
                    notes=mc.notes,
                    order_index=mc.order_index or 0,
                    days_count=mc.days_count,
                    schedule_json=mc.schedule,
                )
            )
        await self.db.commit()
        await self.db.refresh(tpl)
        return await self.get_template(tpl.id)

    async def update_template(self, template_id: int, payload: MesocycleTemplateUpdate) -> MesocycleTemplateResponse:
        stmt = select(MesocycleTemplate).where(
            MesocycleTemplate.id == template_id, MesocycleTemplate.user_id == self.user_id
        )
        res = await self.db.execute(stmt)
        tpl = res.scalars().first()
        if not tpl:
            raise HTTPException(status_code=404, detail="Template not found")
        if payload.name is not None:
            tpl.name = payload.name
        if payload.notes is not None:
            tpl.notes = payload.notes
        if payload.weeks_count is not None:
            tpl.weeks_count = payload.weeks_count
        if payload.microcycle_length_days is not None:
            tpl.microcycle_length_days = payload.microcycle_length_days
        if payload.normalization_value is not None:
            tpl.normalization_value = payload.normalization_value
        if payload.normalization_unit is not None:
            tpl.normalization_unit = payload.normalization_unit
        if payload.is_public is not None:
            tpl.is_public = payload.is_public
        await self.db.flush()
        if payload.microcycles is not None:
            # replace all microcycles
            stmt_mc = select(MicrocycleTemplate).where(MicrocycleTemplate.mesocycle_template_id == tpl.id)
            res_mc = await self.db.execute(stmt_mc)
            for mc in res_mc.scalars().all():
                await self.db.delete(mc)
            for mc in payload.microcycles:
                self.db.add(
                    MicrocycleTemplate(
                        mesocycle_template_id=tpl.id,
                        name=mc.name,
                        notes=mc.notes,
                        order_index=mc.order_index or 0,
                        days_count=mc.days_count,
                        schedule_json=mc.schedule,
                    )
                )
        await self.db.commit()
        await self.db.refresh(tpl)
        return await self.get_template(tpl.id)

    async def delete_template(self, template_id: int) -> None:
        stmt = select(MesocycleTemplate).where(
            MesocycleTemplate.id == template_id, MesocycleTemplate.user_id == self.user_id
        )
        res = await self.db.execute(stmt)
        tpl = res.scalars().first()
        if not tpl:
            return
        await self.db.delete(tpl)
        await self.db.commit()

    def _to_response(self, tpl: MesocycleTemplate) -> MesocycleTemplateResponse:
        mcs = [
            MicrocycleTemplateDto.model_validate(
                {
                    "id": mc.id,
                    "name": mc.name,
                    "notes": mc.notes,
                    "order_index": mc.order_index,
                    "days_count": mc.days_count,
                    "schedule": mc.schedule_json,
                }
            )
            for mc in tpl.microcycles
        ]
        return MesocycleTemplateResponse(
            id=tpl.id,
            user_id=tpl.user_id,
            name=tpl.name,
            notes=tpl.notes,
            weeks_count=tpl.weeks_count,
            microcycle_length_days=tpl.microcycle_length_days,
            normalization_value=tpl.normalization_value,
            normalization_unit=tpl.normalization_unit,
            is_public=tpl.is_public,
            microcycles=mcs,
        )

    async def instantiate_into_plan(self, plan_id: int, body: InstantiateFromTemplateRequest) -> int:
        # returns created mesocycle id
        await self._require_plan(plan_id)
        # load template (public or owned)
        stmt = select(MesocycleTemplate).where(MesocycleTemplate.id == body.template_id)
        res = await self.db.execute(stmt)
        tpl = res.scalars().first()
        if not tpl or (not tpl.is_public and tpl.user_id != self.user_id):
            raise HTTPException(status_code=404, detail="Template not found")

        # compute insertion order_index based on placement
        insert_after_index: int | None = None
        if body.placement.mode == PlacementMode.Insert_After_Mesocycle:
            insert_after_index = max(0, int((body.placement.mesocycle_index or 0)))
        elif body.placement.mode == PlacementMode.Insert_After_Workout:
            # Map workout to mesocycle index by order
            insert_after_index = await self._resolve_mesocycle_index_by_workout(plan_id, body.placement.workout_id)
        else:
            # Append to end: after last index
            insert_after_index = await self._get_last_mesocycle_index(plan_id)

        # shift forward if needed
        await self._shift_mesocycles(plan_id, after_index=insert_after_index)

        # create mesocycle
        new_meso = Mesocycle(
            calendar_plan_id=plan_id,
            name=tpl.name,
            notes=tpl.notes,
            order_index=insert_after_index + 1,
            weeks_count=tpl.weeks_count,
            microcycle_length_days=tpl.microcycle_length_days,
            duration_weeks=tpl.weeks_count or 0,
        )
        self.db.add(new_meso)
        await self.db.flush()

        # create microcycles + schedule
        for tm in tpl.microcycles:
            mc = Microcycle(
                mesocycle_id=new_meso.id,
                name=tm.name,
                notes=tm.notes,
                order_index=tm.order_index or 0,
                days_count=tm.days_count,
                normalization_value=getattr(tm, "normalization_value", None),
                normalization_unit=getattr(tm, "normalization_unit", None),
                normalization_rules=(getattr(tm, "normalization_rules", None) or None),
            )
            self.db.add(mc)
            await self.db.flush()
            schedule = tm.schedule_json or {}
            # iterate days in order
            for raw_day, items in schedule.items():
                try:
                    day_idx = int(str(raw_day).strip().split()[-1])
                except Exception:
                    day_idx = None
                if day_idx is None:
                    continue
                pw = PlanWorkout(
                    microcycle_id=mc.id,
                    day_label=f"Day {day_idx}",
                    order_index=day_idx - 1,
                )
                self.db.add(pw)
                await self.db.flush()
                for item in items or []:
                    ex_id = item.get("exercise_id") or item.get("exercise_list_id")
                    if ex_id is None:
                        continue
                    name = item.get("name") or ""
                    pe = PlanExercise(
                        plan_workout_id=pw.id,
                        exercise_definition_id=int(ex_id),
                        exercise_name=name,
                    )
                    self.db.add(pe)
                    await self.db.flush()
                    for s in item.get("sets") or []:
                        self.db.add(
                            PlanSet(
                                plan_exercise_id=pe.id,
                                order_index=0,  # will be reindexed by natural order
                                intensity=s.get("intensity"),
                                effort=s.get("effort"),
                                volume=s.get("volume"),
                                working_weight=s.get("working_weight"),
                            )
                        )
        await self.db.commit()
        return new_meso.id

    async def instantiate_from_existing(self, plan_id: int, body: InstantiateFromExistingRequest) -> int:
        """Clone existing mesocycle (of the same user) by id into target plan with placement policy."""
        await self._require_plan(plan_id)
        # Load source mesocycle with full graph, enforce ownership by user
        stmt = (
            select(Mesocycle)
            .options(
                selectinload(Mesocycle.microcycles)
                .selectinload(Microcycle.plan_workouts)
                .selectinload(PlanWorkout.exercises)
                .selectinload(PlanExercise.sets)
            )
            .join(Mesocycle.calendar_plan)
            .where(Mesocycle.id == int(body.source_mesocycle_id))
            .where(CalendarPlan.user_id == self.user_id)
        )
        res = await self.db.execute(stmt)
        src: Mesocycle | None = res.scalars().first()
        if not src:
            raise HTTPException(status_code=404, detail="Source mesocycle not found or access denied")

        # placement anchor
        if body.placement.mode == PlacementMode.Insert_After_Mesocycle:
            insert_after_index = max(0, int((body.placement.mesocycle_index or 0)))
        elif body.placement.mode == PlacementMode.Insert_After_Workout:
            insert_after_index = await self._resolve_mesocycle_index_by_workout(plan_id, body.placement.workout_id)
        else:
            insert_after_index = await self._get_last_mesocycle_index(plan_id)

        await self._shift_mesocycles(plan_id, after_index=insert_after_index)

        # Create mesocycle clone
        weeks_count = src.weeks_count
        try:
            # fallback if null
            if weeks_count is None:
                weeks_count = len(src.microcycles or [])
        except Exception:
            weeks_count = 0
        new_meso = Mesocycle(
            calendar_plan_id=plan_id,
            name=src.name,
            notes=src.notes,
            order_index=insert_after_index + 1,
            weeks_count=weeks_count,
            microcycle_length_days=src.microcycle_length_days,
            duration_weeks=src.duration_weeks
            if getattr(src, "duration_weeks", None) is not None
            else (weeks_count or 0),
        )
        self.db.add(new_meso)
        await self.db.flush()

        # Clone microcycles graph in order
        for mc_src in sorted(src.microcycles or [], key=lambda m: (m.order_index, m.id)):
            mc_new = Microcycle(
                mesocycle_id=new_meso.id,
                name=mc_src.name,
                notes=mc_src.notes,
                order_index=mc_src.order_index or 0,
                normalization_value=getattr(mc_src, "normalization_value", None),
                normalization_unit=getattr(mc_src, "normalization_unit", None),
                normalization_rules=getattr(mc_src, "normalization_rules", None),
                days_count=mc_src.days_count,
            )
            self.db.add(mc_new)
            await self.db.flush()
            # Workouts
            for pw_src in sorted(mc_src.plan_workouts or [], key=lambda w: (w.order_index, w.id)):
                pw_new = PlanWorkout(
                    microcycle_id=mc_new.id,
                    day_label=pw_src.day_label,
                    order_index=pw_src.order_index or 0,
                )
                self.db.add(pw_new)
                await self.db.flush()
                # Exercises
                for ex_src in sorted(pw_src.exercises or [], key=lambda e: (e.order_index, e.id)):
                    ex_new = PlanExercise(
                        plan_workout_id=pw_new.id,
                        exercise_definition_id=ex_src.exercise_definition_id,
                        exercise_name=ex_src.exercise_name,
                        order_index=ex_src.order_index or 0,
                    )
                    self.db.add(ex_new)
                    await self.db.flush()
                    # Sets
                    for s_src in sorted(ex_src.sets or [], key=lambda s: (s.order_index, s.id)):
                        self.db.add(
                            PlanSet(
                                plan_exercise_id=ex_new.id,
                                order_index=s_src.order_index or 0,
                                intensity=s_src.intensity,
                                effort=s_src.effort,
                                volume=s_src.volume,
                                working_weight=s_src.working_weight,
                            )
                        )

        await self.db.commit()
        return new_meso.id

    async def _get_last_mesocycle_index(self, plan_id: int) -> int:
        stmt = (
            select(Mesocycle)
            .where(Mesocycle.calendar_plan_id == plan_id)
            .order_by(Mesocycle.order_index.desc(), Mesocycle.id.desc())
        )
        res = await self.db.execute(stmt)
        last = res.scalars().first()
        return last.order_index if last else 0

    async def _resolve_mesocycle_index_by_workout(self, plan_id: int, workout_id: Optional[int]) -> int:
        if not workout_id:
            return await self._get_last_mesocycle_index(plan_id)
        # Find applied plan of this user that references the workout, and derive mesocycle order_index
        stmt = (
            select(AppliedMesocycle.order_index)
            .select_from(AppliedWorkout)
            .join(AppliedMicrocycle, AppliedMicrocycle.id == AppliedWorkout.applied_microcycle_id)
            .join(AppliedMesocycle, AppliedMesocycle.id == AppliedMicrocycle.applied_mesocycle_id)
            .join(AppliedCalendarPlan, AppliedCalendarPlan.id == AppliedMesocycle.applied_plan_id)
            .where(AppliedWorkout.workout_id == int(workout_id))
            .where(AppliedCalendarPlan.calendar_plan_id == plan_id)
            .where(AppliedCalendarPlan.user_id == self.user_id)
            .order_by(AppliedCalendarPlan.id.desc())
        )
        res = await self.db.execute(stmt)
        row = res.first()
        if row and row[0] is not None:
            try:
                return int(row[0])
            except Exception:
                pass
        return await self._get_last_mesocycle_index(plan_id)

    async def _shift_mesocycles(self, plan_id: int, after_index: int) -> None:
        # Increment order_index for mesocycles with order_index > after_index
        stmt = (
            select(Mesocycle)
            .where(Mesocycle.calendar_plan_id == plan_id)
            .order_by(Mesocycle.order_index.asc(), Mesocycle.id.asc())
        )
        res = await self.db.execute(stmt)
        items = list(res.scalars().all())
        for m in items:
            if m.order_index > after_index:
                m.order_index = m.order_index + 1
        await self.db.flush()
