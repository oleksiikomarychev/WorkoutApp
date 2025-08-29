from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from ..dependencies import get_db, get_user_id
from ..schemas.calendar_plan import (
    CalendarPlanCreate,
    CalendarPlanUpdate,
    CalendarPlanResponse,
)
from ..services.calendar_plan_service import CalendarPlanService

router = APIRouter()


@router.post(
    "", response_model=CalendarPlanResponse, status_code=status.HTTP_201_CREATED
)
async def create_calendar_plan(
    plan_data: CalendarPlanCreate = Body(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """Создание нового календарного плана"""
    service = CalendarPlanService(db)
    try:
        return service.create_plan(plan_data, user_id=user_id)
    except ValueError as e:
        # For example: missing exercise IDs in schedule
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )


@router.get("", response_model=List[CalendarPlanResponse])
async def get_all_plans(
    db: Session = Depends(get_db), user_id: str = Depends(get_user_id)
) -> List[CalendarPlanResponse]:
    """Получение всех планов"""
    service = CalendarPlanService(db)
    return service.get_all_plans(user_id=user_id)


# Favorites endpoints
@router.get("/favorites", response_model=List[CalendarPlanResponse])
async def get_favorite_plans(
    db: Session = Depends(get_db), user_id: str = Depends(get_user_id)
) -> List[CalendarPlanResponse]:
    """Список избранных планов"""
    service = CalendarPlanService(db)
    return service.get_favorite_plans(user_id=user_id)


@router.get("/{plan_id}", response_model=CalendarPlanResponse)
async def get_calendar_plan(
    plan_id: int, db: Session = Depends(get_db), user_id: str = Depends(get_user_id)
):
    """Получение плана по ID"""
    service = CalendarPlanService(db)
    plan = service.get_plan(plan_id, user_id=user_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.get("/{plan_id}/workouts", response_model=List[Dict[str, Any]])
async def get_plan_workouts(
    plan_id: int, db: Session = Depends(get_db), user_id: str = Depends(get_user_id)
) -> List[Dict[str, Any]]:
    """Получение списка тренировок по плану"""
    service = CalendarPlanService(db)
    return service.generate_workouts(plan_id, user_id=user_id)


@router.put("/{plan_id}", response_model=CalendarPlanResponse)
async def update_calendar_plan(
    plan_id: int,
    plan_data: CalendarPlanUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """Обновление плана"""
    service = CalendarPlanService(db)
    try:
        return service.update_plan(plan_id, plan_data, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_calendar_plan(
    plan_id: int, db: Session = Depends(get_db), user_id: str = Depends(get_user_id)
):
    """Удаление плана"""
    service = CalendarPlanService(db)
    service.delete_plan(plan_id, user_id=user_id)


@router.post(
    "/{plan_id}/favorite",
    response_model=CalendarPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_favorite_plan(
    plan_id: int, db: Session = Depends(get_db), user_id: str = Depends(get_user_id)
):
    """Добавить план в избранные"""
    service = CalendarPlanService(db)
    try:
        return service.add_favorite(plan_id, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{plan_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite_plan(
    plan_id: int, db: Session = Depends(get_db), user_id: str = Depends(get_user_id)
):
    """Удалить план из избранных"""
    service = CalendarPlanService(db)
    service.remove_favorite(plan_id, user_id=user_id)
