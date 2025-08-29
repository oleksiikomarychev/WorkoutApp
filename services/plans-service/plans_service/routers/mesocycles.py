from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..dependencies import get_db, get_user_id
from ..services.mesocycle_service import MesocycleService
from ..schemas.mesocycle import (
    MesocycleCreate,
    MesocycleUpdate,
    MesocycleResponse,
    MicrocycleCreate,
    MicrocycleUpdate,
    MicrocycleResponse,
)

router = APIRouter()


# ===== Mesocycles =====
@router.get(
    "/calendar-plans/{plan_id}/mesocycles", response_model=List[MesocycleResponse]
)
def list_mesocycles(
    plan_id: int, db: Session = Depends(get_db), user_id: str = Depends(get_user_id)
):
    svc = MesocycleService(db)
    return svc.list_mesocycles(plan_id, user_id)


@router.post(
    "/calendar-plans/{plan_id}/mesocycles",
    response_model=MesocycleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_mesocycle(
    plan_id: int,
    body: MesocycleUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    # Reuse MesocycleUpdate fields for simple creation from path plan_id
    data = MesocycleCreate(
        calendar_plan_id=plan_id,
        name=body.name or "Mesocycle",
        notes=body.notes,
        order_index=body.order_index or 0,
        normalization_value=body.normalization_value,
        normalization_unit=body.normalization_unit,
        weeks_count=body.weeks_count,
        microcycle_length_days=body.microcycle_length_days,
    )
    svc = MesocycleService(db)
    return svc.create_mesocycle(data, user_id)


@router.put("/mesocycles/{mesocycle_id}", response_model=MesocycleResponse)
def update_mesocycle(
    mesocycle_id: int,
    body: MesocycleUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    svc = MesocycleService(db)
    return svc.update_mesocycle(mesocycle_id, body, user_id)


@router.delete(
    "/mesocycles/{mesocycle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_mesocycle(
    mesocycle_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    svc = MesocycleService(db)
    svc.delete_mesocycle(mesocycle_id, user_id)
    return None


# ===== Microcycles =====
@router.get(
    "/mesocycles/{mesocycle_id}/microcycles", response_model=List[MicrocycleResponse]
)
def list_microcycles(
    mesocycle_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    svc = MesocycleService(db)
    return svc.list_microcycles(mesocycle_id, user_id)


@router.post(
    "/mesocycles/{mesocycle_id}/microcycles",
    response_model=MicrocycleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_microcycle(
    mesocycle_id: int,
    body: MicrocycleUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
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
    svc = MesocycleService(db)
    return svc.create_microcycle(data, user_id)


@router.put("/microcycles/{microcycle_id}", response_model=MicrocycleResponse)
def update_microcycle(
    microcycle_id: int,
    body: MicrocycleUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    svc = MesocycleService(db)
    return svc.update_microcycle(microcycle_id, body, user_id)


@router.delete(
    "/microcycles/{microcycle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_microcycle(
    microcycle_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    svc = MesocycleService(db)
    svc.delete_microcycle(microcycle_id, user_id)
    return None
