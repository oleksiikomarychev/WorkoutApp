from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_db, get_current_user_id
from ..schemas.templates import (
    MesocycleTemplateCreate, MesocycleTemplateUpdate, MesocycleTemplateResponse,
    InstantiateFromTemplateRequest,
)
from ..services.template_service import TemplateService

router = APIRouter(prefix="/mesocycle-templates", tags=["Mesocycle Templates"]) 


@router.get("/", response_model=List[MesocycleTemplateResponse])
async def list_templates(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    svc = TemplateService(db, user_id)
    return await svc.list_templates()


@router.post("/", response_model=MesocycleTemplateResponse)
async def create_template(
    body: MesocycleTemplateCreate = Body(...),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    svc = TemplateService(db, user_id)
    return await svc.create_template(body)


@router.get("/{template_id}", response_model=MesocycleTemplateResponse)
async def get_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    svc = TemplateService(db, user_id)
    return await svc.get_template(template_id)


@router.put("/{template_id}", response_model=MesocycleTemplateResponse)
async def update_template(
    template_id: int,
    body: MesocycleTemplateUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    svc = TemplateService(db, user_id)
    return await svc.update_template(template_id, body)


@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    svc = TemplateService(db, user_id)
    await svc.delete_template(template_id)
    return {"status": "ok"}


@router.post("/calendar-plans/{plan_id}/from-template", response_model=int)
async def instantiate_template_into_plan(
    plan_id: int,
    body: InstantiateFromTemplateRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    svc = TemplateService(db, user_id)
    return await svc.instantiate_into_plan(plan_id, body)
