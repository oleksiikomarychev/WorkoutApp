from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.dependencies import get_db
from app.schemas.calendar_plan import (
    CalendarPlanInstanceCreate,
    CalendarPlanInstanceUpdate,
    CalendarPlanInstanceResponse,
)
from app.services.calendar_plan_instance_service import CalendarPlanInstanceService
from app.services.applied_calendar_plan_service import AppliedCalendarPlanService
from app.schemas.calendar_plan import ApplyPlanRequest, AppliedCalendarPlanResponse

router = APIRouter()

@router.get("", response_model=List[CalendarPlanInstanceResponse])
async def list_instances(db: Session = Depends(get_db)) -> List[CalendarPlanInstanceResponse]:
    service = CalendarPlanInstanceService(db)
    return service.list_instances()

@router.post("", response_model=CalendarPlanInstanceResponse, status_code=status.HTTP_201_CREATED)
async def create_instance(payload: CalendarPlanInstanceCreate, db: Session = Depends(get_db)) -> CalendarPlanInstanceResponse:
    service = CalendarPlanInstanceService(db)
    return service.create(payload)

@router.get("/{instance_id}", response_model=CalendarPlanInstanceResponse)
async def get_instance(instance_id: int, db: Session = Depends(get_db)) -> CalendarPlanInstanceResponse:
    service = CalendarPlanInstanceService(db)
    inst = service.get_instance(instance_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Instance not found")
    return inst

@router.put("/{instance_id}", response_model=CalendarPlanInstanceResponse)
async def update_instance(instance_id: int, payload: CalendarPlanInstanceUpdate, db: Session = Depends(get_db)) -> CalendarPlanInstanceResponse:
    service = CalendarPlanInstanceService(db)
    try:
        return service.update(instance_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_instance(instance_id: int, db: Session = Depends(get_db)):
    service = CalendarPlanInstanceService(db)
    service.delete_instance(instance_id)

@router.post("/from-plan/{plan_id}", response_model=CalendarPlanInstanceResponse, status_code=status.HTTP_201_CREATED)
async def create_from_plan(plan_id: int, db: Session = Depends(get_db)) -> CalendarPlanInstanceResponse:
    service = CalendarPlanInstanceService(db)
    try:
        return service.create_from_plan(plan_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{instance_id}/apply", response_model=AppliedCalendarPlanResponse)
async def apply_from_instance(instance_id: int, payload: ApplyPlanRequest, db: Session = Depends(get_db)) -> AppliedCalendarPlanResponse:
    """Применить текущую редактируемую версию плана (instance) с выбранными user max и настройками"""
    service = AppliedCalendarPlanService(db)
    try:
        return service.apply_plan_from_instance(instance_id, payload.user_max_ids, payload.compute)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
