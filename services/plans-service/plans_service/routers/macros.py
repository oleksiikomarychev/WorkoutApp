from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from ..dependencies import get_db, get_current_user_id
from ..models.calendar import CalendarPlan
from ..models.macro import PlanMacro
from ..schemas.macro import (
    PlanMacroCreate,
    PlanMacroUpdate,
    PlanMacroResponse,
)

router = APIRouter(prefix="/calendar-plans/{plan_id}/macros", tags=["plan-macros"]) 


async def _require_plan(db: AsyncSession, plan_id: int, user_id: str) -> CalendarPlan:
    stmt = (
        select(CalendarPlan)
        .where(CalendarPlan.id == plan_id)
        .where(CalendarPlan.user_id == user_id)
    )
    res = await db.execute(stmt)
    plan = res.scalars().first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.get("/", response_model=List[PlanMacroResponse])
async def list_macros(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> List[PlanMacroResponse]:
    await _require_plan(db, plan_id, user_id)
    stmt = (
        select(PlanMacro)
        .where(PlanMacro.calendar_plan_id == plan_id)
        .order_by(PlanMacro.priority.asc(), PlanMacro.id.asc())
    )
    res = await db.execute(stmt)
    items = res.scalars().all()
    return [
        PlanMacroResponse(
            id=i.id,
            calendar_plan_id=i.calendar_plan_id,
            name=i.name,
            is_active=i.is_active,
            priority=i.priority,
            rule=_safe_parse_json(i.rule_json),
            created_at=i.created_at,
            updated_at=i.updated_at,
        )
        for i in items
    ]


@router.post("/", response_model=PlanMacroResponse, status_code=status.HTTP_201_CREATED)
async def create_macro(
    plan_id: int,
    payload: PlanMacroCreate = Body(...),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> PlanMacroResponse:
    await _require_plan(db, plan_id, user_id)
    rule_payload = payload.rule.model_dump()

    data = PlanMacro(
        calendar_plan_id=plan_id,
        name=payload.name,
        is_active=payload.is_active,
        priority=payload.priority,
        rule_json=_safe_dump_json(rule_payload),
    )
    db.add(data)
    await db.flush()
    await db.commit()
    await db.refresh(data)
    return PlanMacroResponse(
        id=data.id,
        calendar_plan_id=data.calendar_plan_id,
        name=data.name,
        is_active=data.is_active,
        priority=data.priority,
        rule=_safe_parse_json(data.rule_json),
        created_at=data.created_at,
        updated_at=data.updated_at,
    )


@router.put("/{macro_id}", response_model=PlanMacroResponse)
async def update_macro(
    plan_id: int,
    macro_id: int,
    payload: PlanMacroUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> PlanMacroResponse:
    await _require_plan(db, plan_id, user_id)
    stmt = select(PlanMacro).where(PlanMacro.id == macro_id, PlanMacro.calendar_plan_id == plan_id)
    res = await db.execute(stmt)
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="Macro not found")

    if payload.name is not None:
        obj.name = payload.name
    if payload.is_active is not None:
        obj.is_active = payload.is_active
    if payload.priority is not None:
        obj.priority = payload.priority
    if payload.rule is not None:
        obj.rule_json = _safe_dump_json(payload.rule.model_dump())
    await db.flush()
    await db.commit()
    await db.refresh(obj)
    return PlanMacroResponse(
        id=obj.id,
        calendar_plan_id=obj.calendar_plan_id,
        name=obj.name,
        is_active=obj.is_active,
        priority=obj.priority,
        rule=_safe_parse_json(obj.rule_json),
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


@router.delete("/{macro_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_macro(
    plan_id: int,
    macro_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    await _require_plan(db, plan_id, user_id)
    stmt = delete(PlanMacro).where(PlanMacro.id == macro_id, PlanMacro.calendar_plan_id == plan_id)
    res = await db.execute(stmt)
    await db.commit()
    # No explicit rows-affected check to avoid leaking existence; 204 regardless
    return


# --- helpers ---
import json

def _safe_parse_json(s: str | None):
    if not s:
        return {}
    try:
        v = json.loads(s)
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}


def _safe_dump_json(obj: dict) -> str:
    try:
        if hasattr(obj, "model_dump"):
            obj = obj.model_dump()
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        # store empty object on failure
        return "{}"
