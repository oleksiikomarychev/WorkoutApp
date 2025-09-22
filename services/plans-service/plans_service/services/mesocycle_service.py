from typing import List, Optional, Dict, Any
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from fastapi import HTTPException, status

from ..models.calendar import CalendarPlan, Mesocycle, Microcycle
from ..schemas.mesocycle import (
    MesocycleCreate,
    MesocycleUpdate,
    MesocycleResponse,
    MicrocycleCreate,
    MicrocycleUpdate,
    MicrocycleResponse,
)


class MesocycleService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _check_plan_permission(self, plan_id: int, user_id: str) -> CalendarPlan:
        stmt = select(CalendarPlan).where(CalendarPlan.id == plan_id, CalendarPlan.user_id == user_id)
        result = await self.db.execute(stmt)
        plan = result.scalars().first()
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found or permission denied")
        return plan

    async def _check_mesocycle_permission(self, mesocycle_id: int, user_id: Optional[str]) -> Optional[Mesocycle]:
        stmt = select(Mesocycle).options(joinedload(Mesocycle.applied_calendar_plan)).where(Mesocycle.id == mesocycle_id)
        result = await self.db.execute(stmt)
        meso = result.scalars().first()
        if not meso:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mesocycle not found")
        if meso.applied_calendar_plan and meso.applied_calendar_plan.user_id is not None and meso.applied_calendar_plan.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        return meso

    async def _check_microcycle_permission(self, microcycle_id: int, user_id: str) -> Microcycle:
        stmt = select(Microcycle).options(joinedload(Microcycle.mesocycle).joinedload(Mesocycle.applied_calendar_plan)).where(Microcycle.id == microcycle_id)
        result = await self.db.execute(stmt)
        micro = result.scalars().first()
        if not micro:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Microcycle not found")
        if micro.mesocycle.applied_calendar_plan and micro.mesocycle.applied_calendar_plan.user_id is not None and micro.mesocycle.applied_calendar_plan.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
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

    async def list_mesocycles(self, plan_id: int, user_id: str) -> List[MesocycleResponse]:
        try:
            stmt = select(CalendarPlan).where(CalendarPlan.id == plan_id, or_(CalendarPlan.user_id == user_id, CalendarPlan.user_id.is_(None)))
            result = await self.db.execute(stmt)
            plan = result.scalars().first()
            if not plan:
                raise HTTPException(status_code=404, detail="Plan not found or permission denied")
            stmt = select(Mesocycle).where(Mesocycle.calendar_plan_id == plan_id).order_by(Mesocycle.order_index.asc(), Mesocycle.id.asc())
            result = await self.db.execute(stmt)
            meso = result.scalars().all()
            return [MesocycleResponse.model_validate(m) for m in meso]
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to list mesocycles: {str(e)}")

    async def create_mesocycle(self, data: MesocycleCreate, user_id: str) -> MesocycleResponse:
        try:
            await self._check_plan_permission(data.calendar_plan_id, user_id)
            order_index = (data.order_index if (data.order_index is not None and data.order_index > 0) else None)
            if order_index is None:
                stmt = select(Mesocycle).where(Mesocycle.calendar_plan_id == data.calendar_plan_id).order_by(Mesocycle.order_index.desc(), Mesocycle.id.desc())
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
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create mesocycle: {str(e)}")

    async def update_mesocycle(self, mesocycle_id: int, data: MesocycleUpdate, user_id: str) -> MesocycleResponse:
        m = await self._check_mesocycle_permission(mesocycle_id, user_id)
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

    async def delete_mesocycle(self, mesocycle_id: int, user_id: str) -> None:
        m = await self._check_mesocycle_permission(mesocycle_id, user_id)
        self.db.delete(m)
        await self.db.commit()

    async def get_mesocycle_by_id(self, mesocycle_id: int) -> Optional[Mesocycle]:
        stmt = select(Mesocycle).options(selectinload(Mesocycle.microcycles)).where(Mesocycle.id == mesocycle_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_microcycles(self, mesocycle_id: int, user_id: str) -> List[MicrocycleResponse]:
        meso = await self._check_mesocycle_permission(mesocycle_id, user_id)
        stmt = select(Microcycle).where(Microcycle.mesocycle_id == mesocycle_id).order_by(Microcycle.order_index.asc(), Microcycle.id.asc())
        result = await self.db.execute(stmt)
        micro = result.scalars().all()
        return [MicrocycleResponse.model_validate(mc) for mc in micro]

    async def create_microcycle(self, data: MicrocycleCreate, user_id: str) -> MicrocycleResponse:
        meso = await self._check_mesocycle_permission(data.mesocycle_id, user_id)
        if not meso:
            raise HTTPException(status_code=404, detail="Mesocycle not found")
        try:
            order_index = (data.order_index if (data.order_index is not None and data.order_index > 0) else None)
            if order_index is None:
                stmt = select(Microcycle).where(Microcycle.mesocycle_id == data.mesocycle_id).order_by(Microcycle.order_index.desc(), Microcycle.id.desc())
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
                days_count=data.days_count,
            )
            self.db.add(mc)
            await self.db.commit()
            await self.db.refresh(mc)
            return MicrocycleResponse.model_validate(mc)
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create microcycle: {str(e)}")

    async def update_microcycle(self, microcycle_id: int, data: MicrocycleUpdate, user_id: str) -> MicrocycleResponse:
        mc = await self._check_microcycle_permission(microcycle_id, user_id)
        if data.name is not None:
            mc.name = data.name
        if data.notes is not None:
            mc.notes = data.notes
        if data.order_index is not None:
            mc.order_index = data.order_index
        if data.schedule is not None:
            mc.schedule = await self._serialize_schedule(data.schedule)
        if data.normalization_value is not None:
            mc.normalization_value = data.normalization_value
        if data.normalization_unit is not None:
            mc.normalization_unit = data.normalization_unit
        if data.days_count is not None:
            mc.days_count = data.days_count
        await self.db.commit()
        await self.db.refresh(mc)
        return MicrocycleResponse.model_validate(mc)

    async def delete_microcycle(self, microcycle_id: int, user_id: str) -> None:
        mc = await self._check_microcycle_permission(microcycle_id, user_id)
        self.db.delete(mc)
        await self.db.commit()

    async def get_microcycle_by_id(self, microcycle_id: int) -> Optional[Microcycle]:
        stmt = select(Microcycle).where(Microcycle.id == microcycle_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()
