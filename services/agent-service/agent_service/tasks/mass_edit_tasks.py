"""Celery tasks for mass-edit operations."""

from __future__ import annotations

import asyncio
from typing import Any, Dict

from celery import shared_task
from celery.utils.log import get_task_logger

from ..celery_app import TOOLS_TASK_QUEUE
from ..prompts.mass_edit import build_plan_mass_edit_agent_prompt
from ..services.entity_resolver import build_applied_mass_edit_filter_hints, parse_inline_references
from ..services.mass_edit import (
    apply_applied_mass_edit_to_plan,
    apply_mass_edit_to_plan,
    create_plan_mass_edit_tool,
    generate_applied_mass_edit_command,
    generate_mass_edit_command,
    shift_applied_plan_schedule,
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
    arguments_prompt = build_plan_mass_edit_agent_prompt(plan_id, normalized_mode, prompt)

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


@shared_task(
    bind=True,
    name="agent.applied_mass_edit.direct",
    queue=TOOLS_TASK_QUEUE,
    max_retries=2,
)
def execute_applied_mass_edit_task(
    self,
    *,
    applied_plan_id: int,
    user_id: str,
    mode: str,
    prompt: str,
) -> Dict[str, Any]:
    """Generate an applied-plan mass-edit command via LLM and apply it to an applied plan."""

    normalized_mode = _normalize_mode(mode)
    try:
        inline_refs = parse_inline_references(prompt)
        filter_hints: Dict[str, Any] = {}
        if inline_refs:
            filter_hints = _run_async(
                build_applied_mass_edit_filter_hints(
                    inline_refs,
                    active_applied_plan_id=applied_plan_id,
                )
            )

        command = _run_async(generate_applied_mass_edit_command(prompt, normalized_mode))

        if isinstance(filter_hints, dict) and filter_hints:
            flt = command.get("filter")
            if not isinstance(flt, dict):
                flt = {}

            hinted_po = filter_hints.get("plan_order_indices")
            existing_po = flt.get("plan_order_indices")
            if hinted_po:
                if existing_po:
                    try:
                        merged_po = sorted({*existing_po, *hinted_po})
                    except TypeError:
                        merged_po = hinted_po
                    flt["plan_order_indices"] = merged_po
                else:
                    flt["plan_order_indices"] = hinted_po

            hinted_eids = filter_hints.get("exercise_definition_ids")
            existing_eids = flt.get("exercise_definition_ids")
            if hinted_eids:
                if existing_eids:
                    try:
                        merged_eids = sorted({*existing_eids, *hinted_eids})
                    except TypeError:
                        merged_eids = hinted_eids
                    flt["exercise_definition_ids"] = merged_eids
                else:
                    flt["exercise_definition_ids"] = hinted_eids

            command["filter"] = flt

        summary = _run_async(apply_applied_mass_edit_to_plan(applied_plan_id, user_id, command))
        return {
            "variant": "applied_direct",
            "applied_plan_id": applied_plan_id,
            "mode": normalized_mode,
            "summary": summary,
            "mass_edit_command": command,
        }
    except Exception as exc:
        logger.exception("applied_mass_edit_task_failed", exc_info=exc)
        raise self.retry(exc=exc, countdown=60)


@shared_task(
    bind=True,
    name="agent.applied_schedule_shift",
    queue=TOOLS_TASK_QUEUE,
    max_retries=2,
)
def execute_applied_schedule_shift_task(
    self,
    *,
    applied_plan_id: int,
    user_id: str,
    from_date: str,
    days: int = 0,
    to_date: str | None = None,
    new_rest_days: int | None = None,
    action_type: str = "shift",
    only_future: bool = False,
    status_in: list[str] | None = None,
) -> Dict[str, Any]:
    """Shift or restructure schedule of an applied plan."""

    try:
        summary = _run_async(
            shift_applied_plan_schedule(
                applied_plan_id=applied_plan_id,
                user_id=user_id,
                from_date=from_date,
                days=days,
                to_date=to_date,
                new_rest_days=new_rest_days,
                action_type=action_type,
                only_future=only_future,
                status_in=status_in,
            )
        )
        return {
            "variant": "applied_schedule_shift",
            "applied_plan_id": applied_plan_id,
            "from_date": from_date,
            "days": days,
            "action_type": action_type,
            "summary": summary,
        }
    except Exception as exc:
        logger.exception("applied_schedule_shift_task_failed", exc_info=exc)
        raise self.retry(exc=exc, countdown=60)
