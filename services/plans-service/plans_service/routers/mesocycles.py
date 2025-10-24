from typing import List
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..dependencies import get_db, get_current_user_id
from ..models import Microcycle
from ..services.calendar_plan_service import CalendarPlanService
from ..services.mesocycle_service import MesocycleService
from ..schemas.calendar_plan import MesocycleResponse
from ..schemas.calendar_plan import MicrocycleResponse
from ..schemas.mesocycle import (
    MesocycleCreate,
    MesocycleUpdate,
    MesocycleResponse,
    MicrocycleUpdate,
    MicrocycleCreate
)

router = APIRouter(prefix="/mesocycles")


@router.get("/{plan_id}/mesocycles", response_model=List[MesocycleResponse])
async def list_mesocycles(
    plan_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    svc = MesocycleService(db, user_id)
    return await svc.list_mesocycles(plan_id)


@router.post("/{plan_id}/mesocycles", response_model=MesocycleResponse, status_code=status.HTTP_201_CREATED)
async def create_mesocycle(
    plan_id: int,
    body: MesocycleCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    svc = MesocycleService(db, user_id)
    return await svc.create_mesocycle(body)


@router.put("/{mesocycle_id}", response_model=MesocycleResponse)
async def update_mesocycle(
    mesocycle_id: int,
    body: MesocycleUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    svc = MesocycleService(db, user_id)
    return await svc.update_mesocycle(mesocycle_id, body)


@router.delete("/{mesocycle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mesocycle(
    mesocycle_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    svc = MesocycleService(db, user_id)
    await svc.delete_mesocycle(mesocycle_id)
    return None


@router.get("/{mesocycle_id}", response_model=MesocycleResponse)
async def get_mesocycle(
    mesocycle_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    svc = MesocycleService(db, user_id)
    mesocycle = await svc.get_mesocycle_by_id(mesocycle_id)
    if not mesocycle:
        raise HTTPException(status_code=404, detail="Mesocycle not found")
    return mesocycle


@router.get("/{mesocycle_id}/microcycles", response_model=List[MicrocycleResponse])
async def list_microcycles(
    mesocycle_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    svc = MesocycleService(db, user_id)
    return await svc.list_microcycles(mesocycle_id)


@router.post("/{mesocycle_id}/microcycles", response_model=MicrocycleResponse, status_code=status.HTTP_201_CREATED)
async def create_microcycle(
    mesocycle_id: int,
    body: MicrocycleUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    data = MicrocycleCreate(
        mesocycle_id=mesocycle_id,
        name=body.name or "Microcycle",
        notes=body.notes,
        order_index=body.order_index or 0,
        schedule=body.schedule or {},
        normalization_value=body.normalization_value,
        normalization_unit=body.normalization_unit,
        days_count=body.days_count,
    )
    svc = MesocycleService(db, user_id)
    return await svc.create_microcycle(data)


@router.put("/microcycles/{microcycle_id}", response_model=MicrocycleResponse)
async def update_microcycle(
    microcycle_id: int,
    body: MicrocycleUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    svc = MesocycleService(db, user_id)
    return await svc.update_microcycle(microcycle_id, body)


@router.delete("/microcycles/{microcycle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_microcycle(
    microcycle_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    svc = MesocycleService(db, user_id)
    await svc.delete_microcycle(microcycle_id)
    return None



@router.post("/validate")
async def validate_microcycles(
    microcycle_ids: list[int],
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    if not microcycle_ids:
        return {"valid_ids": []}
    
    from ..models.calendar import Mesocycle, CalendarPlan
    # Filter by user ownership through the join chain
    stmt = (
        select(Microcycle.id)
        .join(Microcycle.mesocycle)
        .join(Mesocycle.calendar_plan)
        .where(
            Microcycle.id.in_(microcycle_ids),
            CalendarPlan.user_id == user_id,
        )
    )
    result = await db.execute(stmt)
    valid_ids = [row[0] for row in result.all()]
    return {"valid_ids": valid_ids}


@router.get("/microcycles/{microcycle_id}", response_model=MicrocycleResponse)
async def get_microcycle(
    microcycle_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    svc = MesocycleService(db, user_id)
    microcycle = await svc.get_microcycle_by_id(microcycle_id)
    if not microcycle:
        raise HTTPException(status_code=404, detail="Microcycle not found")
    return microcycle
