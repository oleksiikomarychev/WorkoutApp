from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class PlanMacroBase(BaseModel):
    name: str = Field(..., max_length=255)
    is_active: bool = True
    priority: int = Field(default=100, ge=0, le=10000)
    rule: dict[str, Any] = Field(..., description="Macro rule JSON (5-block DSL)")

    class Config:
        from_attributes = True


class PlanMacroCreate(PlanMacroBase):
    pass


class PlanMacroUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0, le=10000)
    rule: Optional[dict[str, Any]] = None


class PlanMacroResponse(PlanMacroBase):
    id: int
    calendar_plan_id: int
    created_at: datetime
    updated_at: datetime
