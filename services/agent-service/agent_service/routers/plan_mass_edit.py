from fastapi import APIRouter, Depends, HTTPException, status

from ..dependencies import get_current_user_id
from ..schemas.mass_edit import (
    AgentPlanMassEditRequest,
    AgentPlanMassEditResponse,
    AgentPlanMassEditToolResponse,
)
from ..services.mass_edit import (
    generate_mass_edit_command,
    apply_mass_edit_to_plan,
    create_plan_mass_edit_tool,
)
from ..services.tool_agent import run_tools_agent

router = APIRouter(prefix="/agent", tags=["mass_edit"])


@router.post("/plan-mass-edit", response_model=AgentPlanMassEditResponse)
async def plan_mass_edit_endpoint(
    payload: AgentPlanMassEditRequest,
    user_id: str = Depends(get_current_user_id),
) -> AgentPlanMassEditResponse:
    """Обработать запрос пользователя к ЛЛМ и применить mass edit к плану."""

    try:
        command = await generate_mass_edit_command(payload.prompt, payload.mode)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    updated_plan = await apply_mass_edit_to_plan(payload.plan_id, user_id, command)
    return AgentPlanMassEditResponse(plan=updated_plan, mass_edit_command=command)


@router.post("/plan-mass-edit-gpt", response_model=AgentPlanMassEditToolResponse)
async def plan_mass_edit_gpt_endpoint(
    payload: AgentPlanMassEditRequest,
    user_id: str = Depends(get_current_user_id),
) -> AgentPlanMassEditToolResponse:
    tool = create_plan_mass_edit_tool(user_id)

    user_prompt = payload.prompt
    arguments_prompt = (
        f"You must use the `plan_mass_edit` tool if it helps. "
        f"The target plan_id is {payload.plan_id} and default mode is {payload.mode}. "
        f"User instructions: {user_prompt}"
    )

    result = await run_tools_agent(
        user_prompt=arguments_prompt,
        tools=[tool],
        temperature=0.2,
    )

    plan = None
    command = None
    if result.decision_type == "tool_call" and isinstance(result.tool_result, dict):
        plan = result.tool_result.get("plan")
        command = result.tool_result.get("mass_edit_command")

    return AgentPlanMassEditToolResponse(
        decision_type=result.decision_type,
        tool_name=result.tool_name,
        assistant_message=result.answer,
        tool_arguments=result.arguments,
        plan=plan,
        mass_edit_command=command,
        raw_decision=result.raw_decision,
    )
