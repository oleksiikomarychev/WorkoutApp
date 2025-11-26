"""Celery tasks for mass-edit operations."""

from __future__ import annotations

import asyncio
from typing import Any, Dict

from celery import shared_task
from celery.utils.log import get_task_logger

from ..celery_app import TOOLS_TASK_QUEUE
from ..services.mass_edit import (
    apply_mass_edit_to_plan,
    create_plan_mass_edit_tool,
    generate_mass_edit_command,
)
from ..services.tool_agent import run_tools_agent

logger = get_task_logger(__name__)


def _run_async(coro):
    return asyncio.run(coro)


def _normalize_mode(mode: str | None) -> str:
    if not mode:
        return "apply"
    mode_lower = mode.lower()
    return mode_lower if mode_lower in {"apply", "preview"} else "apply"


@shared_task(
    bind=True,
    name="agent.mass_edit.direct",
    queue=TOOLS_TASK_QUEUE,
    max_retries=2,
)
def execute_mass_edit_task(self, *, plan_id: int, user_id: str, mode: str, prompt: str) -> Dict[str, Any]:
    """Generate a mass-edit command via LLM and apply it to a plan."""

    normalized_mode = _normalize_mode(mode)
    try:
        command = _run_async(generate_mass_edit_command(prompt, normalized_mode))
        plan = _run_async(apply_mass_edit_to_plan(plan_id, user_id, command))
        return {
            "variant": "direct",
            "plan": plan,
            "mass_edit_command": command,
            "mode": normalized_mode,
            "plan_id": plan_id,
        }
    except Exception as exc:
        logger.exception("mass_edit_task_failed", exc_info=exc)
        raise self.retry(exc=exc, countdown=60)


@shared_task(
    bind=True,
    name="agent.mass_edit.agent",
    queue=TOOLS_TASK_QUEUE,
    max_retries=2,
)
def execute_mass_edit_agent_task(
    self,
    *,
    plan_id: int,
    user_id: str,
    mode: str,
    prompt: str,
) -> Dict[str, Any]:
    """Execute the tool-driven mass edit flow used by chat/WebSocket commands."""

    normalized_mode = _normalize_mode(mode)
    tool = create_plan_mass_edit_tool(user_id)
    arguments_prompt = (
        "You must use the `plan_mass_edit` tool if it helps. "
        f"The target plan_id is {plan_id} and default mode is {normalized_mode}. "
        f"User instructions: {prompt}"
    )

    try:
        result = _run_async(
            run_tools_agent(
                user_prompt=arguments_prompt,
                tools=[tool],
                temperature=0.2,
            )
        )
    except Exception as exc:
        logger.exception("mass_edit_agent_task_failed", exc_info=exc)
        raise self.retry(exc=exc, countdown=60)

    plan_payload = None
    command_payload = None
    if result.decision_type == "tool_call" and isinstance(result.tool_result, dict):
        plan_payload = result.tool_result.get("plan")
        command_payload = result.tool_result.get("mass_edit_command")

    return {
        "variant": "agent",
        "decision_type": result.decision_type,
        "tool_name": result.tool_name,
        "assistant_message": result.answer,
        "tool_arguments": result.arguments,
        "raw_decision": result.raw_decision,
        "plan": plan_payload,
        "mass_edit_command": command_payload,
        "mode": normalized_mode,
        "plan_id": plan_id,
    }
