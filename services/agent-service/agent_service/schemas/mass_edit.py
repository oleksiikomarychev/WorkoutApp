from typing import Any, Dict, Literal
from pydantic import BaseModel, Field


class AgentPlanMassEditRequest(BaseModel):
    """Запрос на запуск mass edit плана через ЛЛМ."""

    plan_id: int = Field(..., ge=1, description="ID календарного плана пользователя")
    mode: Literal["preview", "apply"] = Field(
        default="apply",
        description="Режим применения: только показать изменения или применить их",
    )
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Текстовый запрос пользователя для ЛЛМ",
    )


class AgentPlanMassEditResponse(BaseModel):
    """Ответ agent-service: обновлённый план и использованная команда mass edit."""

    plan: Dict[str, Any] = Field(..., description="CalendarPlanResponse из plans-service")
    mass_edit_command: Dict[str, Any] = Field(
        ...,
        description="PlanMassEditCommand, который построил ЛЛМ",
    )


class AgentPlanMassEditToolResponse(BaseModel):
    decision_type: Literal["tool_call", "answer", "error"] = Field(...)
    tool_name: str | None = Field(default=None)
    assistant_message: str | None = Field(default=None)
    tool_arguments: Dict[str, Any] = Field(default_factory=dict)
    plan: Dict[str, Any] | None = Field(default=None)
    mass_edit_command: Dict[str, Any] | None = Field(default=None)
    raw_decision: Dict[str, Any] | None = Field(default=None)
