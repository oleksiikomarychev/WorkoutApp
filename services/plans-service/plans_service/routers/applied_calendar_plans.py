from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from ..dependencies import get_db
from ..services.applied_calendar_plan_service import AppliedCalendarPlanService
from ..schemas.calendar_plan import (
    AppliedCalendarPlanResponse,
    AppliedCalendarPlanSummaryResponse,
    ApplyPlanComputeSettings,
)
from typing import Optional, List, Dict, Any

router = APIRouter(prefix="/applied-plans")


@router.get("/active", response_model=Optional[AppliedCalendarPlanResponse])
async def get_active_plan(
    db: Session = Depends(get_db)
):
    """Получение активного плана пользователя"""
    try:
        service = AppliedCalendarPlanService(db)
        return await service.get_active_plan()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch active plan: {str(e)}"
        )


@router.get("/{plan_id}", response_model=AppliedCalendarPlanResponse)
async def get_applied_plan_details(
    plan_id: int, db: Session = Depends(get_db)
):
    """Получение полной информации о примененном плане"""
    try:
        service = AppliedCalendarPlanService(db)
        plan = await service.get_applied_plan_by_id(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Applied plan not found")
        return plan
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch applied plan details: {str(e)}"
        )


@router.get("/user", response_model=List[AppliedCalendarPlanSummaryResponse])
async def get_user_applied_plans(
    db: Session = Depends(get_db)
):
    """Получение всех примененных планов пользователя"""
    try:
        service = AppliedCalendarPlanService(db)
        return await service.get_user_applied_plans()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user applied plans: {str(e)}"
        )


@router.get("", response_model=List[AppliedCalendarPlanResponse])
async def get_applied_plans(db: Session = Depends(get_db)):
    try:
        service = AppliedCalendarPlanService(db)
        return await service.get_user_applied_plans()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch applied plans: {str(e)}"
        )


@router.get("/active/workouts", response_model=List[Dict[str, Any]])
async def get_active_plan_workouts(
    db: Session = Depends(get_db)
):
    """Get ordered workouts for user's active plan"""
    try:
        service = AppliedCalendarPlanService(db)
        active_plan = await service.get_active_plan()
        if not active_plan:
            raise HTTPException(status_code=404, detail="No active plan found")
        
        # Get workouts in order
        workouts = []
        for workout_rel in sorted(active_plan.workouts, key=lambda w: w.order_index):
            # In real implementation, fetch workout details from workout-service
            workouts.append({
                "id": workout_rel.workout_id,
                "order_index": workout_rel.order_index,
                "is_current": workout_rel.order_index == active_plan.current_workout_index
            })
        
        return workouts
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch active plan workouts: {str(e)}"
        )


@router.post("/apply/{plan_id}", response_model=AppliedCalendarPlanResponse)
async def apply_plan(
    plan_id: int,
    compute: ApplyPlanComputeSettings,
    user_max_ids: str = Query(..., description="Comma-separated list of user_max IDs"),
    db: Session = Depends(get_db),
):
    """Применение плана пользователем с настройками вычислений"""
    try:
        # Convert comma-separated string to list of integers, skipping empty parts
        user_max_ids_list = [int(id.strip()) for id in user_max_ids.split(",") if id.strip()]
        if not user_max_ids_list:
            raise HTTPException(status_code=400, detail="At least one user_max_id is required")
        service = AppliedCalendarPlanService(db)
        return await service.apply_plan(plan_id, compute, user_max_ids_list)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply plan: {str(e)}"
        )