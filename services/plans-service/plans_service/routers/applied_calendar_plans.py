from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..dependencies import get_db, get_user_id
from ..services.applied_calendar_plan_service import AppliedCalendarPlanService
from ..schemas.calendar_plan import (
    AppliedCalendarPlanResponse,
    ApplyPlanRequest,
    AppliedCalendarPlanSummaryResponse,
)
from typing import Optional

router = APIRouter()


@router.post("/apply/{plan_id}", response_model=AppliedCalendarPlanResponse)
async def apply_plan(
    plan_id: int,
    payload: ApplyPlanRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """Применение плана пользователем с настройками вычислений"""
    service = AppliedCalendarPlanService(db)
    try:
        return service.apply_plan(
            plan_id, user_id, payload.user_max_ids, payload.compute
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/user", response_model=list[AppliedCalendarPlanSummaryResponse])
async def get_user_applied_plans(
    db: Session = Depends(get_db), user_id: str = Depends(get_user_id)
):
    """Получение всех примененных планов пользователя"""
    service = AppliedCalendarPlanService(db)
    return service.get_user_applied_plans(user_id)


@router.get("/{plan_id}", response_model=AppliedCalendarPlanResponse)
async def get_applied_plan_details(
    plan_id: int, db: Session = Depends(get_db), user_id: str = Depends(get_user_id)
):
    """Получение полной информации о примененном плане"""
    service = AppliedCalendarPlanService(db)
    plan = service.get_applied_plan_by_id(plan_id, user_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Applied plan not found")
    return plan


@router.get("/active", response_model=Optional[AppliedCalendarPlanResponse])
async def get_active_plan(
    db: Session = Depends(get_db), user_id: str = Depends(get_user_id)
):
    """Получение активного плана пользователя"""
    service = AppliedCalendarPlanService(db)
    return service.get_active_plan(user_id)
