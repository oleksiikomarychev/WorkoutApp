from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Dict, Any

from ..dependencies import get_db, get_current_user_id
from ..schemas.calendar_plan import (
    CalendarPlanCreate,
    CalendarPlanUpdate,
    CalendarPlanResponse,
    CalendarPlanSummaryResponse,
    CalendarPlanVariantCreate,
    PlanMassEditCommand,
)
from ..services.calendar_plan_service import CalendarPlanService
from ..models.calendar import CalendarPlan, Mesocycle, Microcycle

router = APIRouter(prefix="/calendar-plans")


@router.post("/", response_model=CalendarPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_calendar_plan(
    plan_data: CalendarPlanCreate = Body(...),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    try:
        result = await CalendarPlanService.create_plan(db, plan_data, user_id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/{plan_id}/variants", response_model=CalendarPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan_variant(
    plan_id: int,
    variant_data: CalendarPlanVariantCreate = Body(...),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    return await CalendarPlanService.create_variant(db, plan_id, user_id, variant_data)


@router.get("/{plan_id}/variants", response_model=List[CalendarPlanSummaryResponse])
async def list_plan_variants(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> List[CalendarPlanSummaryResponse]:
    return await CalendarPlanService.list_variants(db, plan_id, user_id)


@router.get("/", response_model=List[CalendarPlanResponse])
async def get_all_plans(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    roots_only: bool = Query(True, description="Return only original plans (id == root_plan_id)"),
) -> List[CalendarPlanResponse]:
    try:
        return await CalendarPlanService.get_all_plans(db, user_id, roots_only=roots_only)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/favorites", response_model=List[CalendarPlanResponse])
async def get_favorite_plans(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> List[CalendarPlanResponse]:
    try:
        return await CalendarPlanService.get_favorite_plans(db, user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get favorite plans: {str(e)}") from e


@router.get("/{plan_id}", response_model=CalendarPlanResponse)
async def get_calendar_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    try:
        plan = await CalendarPlanService.get_plan(db, plan_id, user_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        # Convert to response model
        plan_data = CalendarPlanResponse.model_validate(plan)
        return plan_data
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/{plan_id}/workouts", response_model=List[Dict[str, Any]])
async def get_plan_workouts(
    plan_id: int, 
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    compute: bool = Query(True, description="Apply normalization computations")
) -> List[Dict[str, Any]]:
    if compute:
        return await CalendarPlanService.generate_workouts(db, plan_id, user_id)
    else:
        # Return base workout structure without computations
        return []


@router.put("/{plan_id}", response_model=CalendarPlanResponse)
async def update_calendar_plan(
    plan_id: int,
    plan_data: CalendarPlanUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    try:
        return await CalendarPlanService.update_plan(db, plan_id, plan_data, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_calendar_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    try:
        await CalendarPlanService.delete_plan(db, plan_id, user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/{plan_id}/mass-edit", response_model=CalendarPlanResponse)
async def mass_edit_calendar_plan(
    plan_id: int,
    cmd: PlanMassEditCommand,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Применить LLM mass-edit/replace операции к упражнениям плана"""
    try:
        return await CalendarPlanService.apply_mass_edit(db, plan_id, user_id, cmd)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e