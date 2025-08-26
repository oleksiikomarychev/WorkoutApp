from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.dependencies import get_db
from app.services.applied_calendar_plan_service import AppliedCalendarPlanService
from app.models.calendar import AppliedCalendarPlan
from app.schemas.calendar_plan import AppliedCalendarPlanResponse, ApplyPlanRequest
from app.schemas.user_max import UserMaxResponse
from typing import List, Optional

router = APIRouter()

@router.post("/apply/{plan_id}", response_model=AppliedCalendarPlanResponse)
async def apply_plan(plan_id: int, payload: ApplyPlanRequest, db: Session = Depends(get_db)):
    """Применение плана пользователем с настройками вычислений"""
    service = AppliedCalendarPlanService(db)
    try:
        return service.apply_plan(plan_id, payload.user_max_ids, payload.compute)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/user", response_model=list[AppliedCalendarPlanResponse])
async def get_user_applied_plans(db: Session = Depends(get_db)):
    """Получение всех примененных планов пользователя"""
    service = AppliedCalendarPlanService(db)
    return service.get_user_applied_plans()

@router.get("/active", response_model=Optional[AppliedCalendarPlanResponse])
async def get_active_plan(db: Session = Depends(get_db)):
    """Получение активного плана пользователя"""
    service = AppliedCalendarPlanService(db)
    return service.get_active_plan()
