from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Dict, Any

from ..dependencies import get_db
from ..schemas.calendar_plan import (
    CalendarPlanCreate,
    CalendarPlanUpdate,
    CalendarPlanResponse,
    FullCalendarPlanCreate
)
from ..services.calendar_plan_service import CalendarPlanService
from ..models.calendar import CalendarPlan, Mesocycle, Microcycle
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar-plans")


@router.post("/", response_model=CalendarPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_calendar_plan(
    plan_data: CalendarPlanCreate = Body(...),
    db: AsyncSession = Depends(get_db),
):
    # Log the incoming request data
    logger.debug(f"Received create plan request: {plan_data}")
    logger.debug(f"Duration weeks value: {plan_data.duration_weeks}")
    
    try:
        result = await CalendarPlanService.create_plan(db, plan_data)
        logger.debug(f"Successfully created plan with duration_weeks={result.duration_weeks}")
        return result
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except Exception as e:
        logger.exception(f"Error creating calendar plan: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/", response_model=List[CalendarPlanResponse])
async def get_all_plans(
    db: AsyncSession = Depends(get_db)
) -> List[CalendarPlanResponse]:
    try:
        return await CalendarPlanService.get_all_plans(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/favorites", response_model=List[CalendarPlanResponse])
async def get_favorite_plans(db: AsyncSession = Depends(get_db)) -> List[CalendarPlanResponse]:
    try:
        return await CalendarPlanService.get_favorite_plans(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get favorite plans: {str(e)}") from e


@router.get("/{plan_id}", response_model=CalendarPlanResponse)
async def get_calendar_plan(
    plan_id: int, db: AsyncSession = Depends(get_db)
):
    try:
        plan = await CalendarPlanService.get_plan(db, plan_id)
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
    compute: bool = Query(True, description="Apply normalization computations")
) -> List[Dict[str, Any]]:
    if compute:
        return await CalendarPlanService.generate_workouts(db, plan_id)
    else:
        # Return base workout structure without computations
        return []


@router.put("/{plan_id}", response_model=CalendarPlanResponse)
async def update_calendar_plan(
    plan_id: int,
    plan_data: CalendarPlanUpdate,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await CalendarPlanService.update_plan(db, plan_id, plan_data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_calendar_plan(
    plan_id: int, db: AsyncSession = Depends(get_db)
):
    try:
        await CalendarPlanService.delete_plan(db, plan_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e