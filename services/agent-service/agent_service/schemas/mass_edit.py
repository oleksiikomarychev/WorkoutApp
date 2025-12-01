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


class AgentAppliedPlanMassEditRequest(BaseModel):
    """Запрос на запуск mass edit уже применённого (applied) плана через ЛЛМ.

    Работает поверх сгенерированных тренировок и их сетов.
    """

    applied_plan_id: int = Field(..., ge=1, description="ID applied-плана пользователя")
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


class AgentAppliedPlanScheduleShiftRequest(BaseModel):
    """Запрос на сдвиг или перепланирование расписания applied-плана."""

    applied_plan_id: int = Field(..., ge=1, description="ID applied-плана пользователя")
    from_date: str = Field(
        ...,
        description="Дата (ISO), начиная с которой нужно сдвигать расписание (обычно понедельник недели)",
    )
    to_date: str | None = Field(
        default=None,
        description="Дата (ISO), до которой (включительно) нужно сдвигать расписание",
    )
    days: int = Field(
        default=0,
        description="На сколько дней сдвинуть запланированные тренировки (может быть отрицательным)",
    )
    new_rest_days: int | None = Field(
        default=None,
        description="Новое количество дней отдыха между тренировками (используется если action_type='set_rest')",
    )
    action_type: Literal["shift", "set_rest"] = Field(
        default="shift",
        description="Тип манипуляции: 'shift' (сдвиг) или 'set_rest' (установка интервалов отдыха)",
    )
    only_future: bool = Field(
        default=False,
        description="Сдвигать только тренировки, ещё не начавшиеся относительно текущего момента",
    )
    status_in: list[str] | None = Field(
        default=None,
        description=("Опциональный список статусов тренировок для сдвига (по умолчанию completed всегда пропускаются)"),
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
