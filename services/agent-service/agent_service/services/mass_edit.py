import logging
from typing import Any, Dict, Literal

import httpx
from fastapi import HTTPException, status

from ..config import settings
from .llm_wrapper import generate_structured_output
from .tool_agent import ToolSpec

logger = logging.getLogger(__name__)

MASS_EDIT_COMMAND_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["operation", "filter", "actions"],
    "properties": {
        "operation": {
            "type": "string",
            "enum": ["mass_edit", "replace_exercises"],
        },
        "mode": {
            "type": "string",
            "enum": ["preview", "apply"],
        },
        "filter": {
            "type": "object",
            "properties": {
                "exercise_name_exact": {"type": "string"},
                "exercise_name_contains": {"type": "string"},
                "intensity_lt": {"type": "number"},
                "intensity_lte": {"type": "number"},
                "intensity_gt": {"type": "number"},
                "intensity_gte": {"type": "number"},
                "volume_lt": {"type": "number"},
                "volume_gt": {"type": "number"},
                "mesocycle_indices": {
                    "type": "array",
                    "items": {"type": "integer", "minimum": 0},
                },
                "microcycle_indices": {
                    "type": "array",
                    "items": {"type": "integer", "minimum": 0},
                },
                "workout_day_labels": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        },
        "actions": {
            "type": "object",
            "properties": {
                "set_intensity": {"type": "number"},
                "increase_intensity_by": {"type": "number"},
                "decrease_intensity_by": {"type": "number"},
                "set_volume": {"type": "number"},
                "increase_volume_by": {"type": "number"},
                "decrease_volume_by": {"type": "number"},
                "replace_exercise_definition_id_to": {"type": "integer"},
                "replace_exercise_name_to": {"type": "string"},
            },
        },
    },
}


MASS_EDIT_PROMPT_TEMPLATE = """
You are an assistant that converts user instructions about editing workout plans into a structured JSON
command for downstream execution. Always respond with JSON matching the provided schema. Do not include
any natural language outside the JSON.

Guidelines:
- operation is usually "mass_edit" unless user explicitly requests a full replacement, then use "replace_exercises".
- Filters should capture the user intent (exercise names, intensity/rpe ranges, days, etc.).
- Actions describe how to update sets (intensity or volume adjustments) or switch exercises.
- Never invent new fields beyond the schema. Numerical values must be raw numbers (e.g., 60 for 60%).
{user_prompt}
"""


async def generate_mass_edit_command(prompt: str, desired_mode: Literal["preview", "apply"]) -> Dict[str, Any]:
    """Call the LLM to transform a natural-language request into PlanMassEditCommand JSON."""

    composed_prompt = MASS_EDIT_PROMPT_TEMPLATE.format(user_prompt=f"User request: {prompt}")
    logger.debug("Generating mass edit command for prompt: %s", prompt)
    command = await generate_structured_output(
        prompt=composed_prompt,
        response_schema=MASS_EDIT_COMMAND_SCHEMA,
        temperature=0.2,
        max_output_tokens=2048,
    )

    if not isinstance(command, dict):
        raise ValueError("LLM response is not a JSON object")

    command.setdefault("operation", "mass_edit")
    command["mode"] = desired_mode

    if "filter" not in command or "actions" not in command:
        raise ValueError("LLM response missing required keys 'filter' or 'actions'")

    return command


async def apply_mass_edit_to_plan(plan_id: int, user_id: str, command: Dict[str, Any]) -> Dict[str, Any]:
    """Proxy the generated command to plans-service and return the updated plan."""

    url = f"{settings.plans_service_url}/plans/calendar-plans/{plan_id}/mass-edit"
    headers = {"X-User-Id": user_id}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, json=command, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.json() if exc.response.headers.get("content-type", "").startswith("application/json") else exc.response.text
        logger.warning("Plans-service mass edit HTTP error: %s", detail)
        raise HTTPException(status_code=exc.response.status_code, detail=detail)
    except httpx.RequestError as exc:
        logger.error("Plans-service mass edit request failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Plans service unavailable")


def create_plan_mass_edit_tool(user_id: str) -> ToolSpec:
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "required": ["plan_id", "mode", "instructions"],
        "properties": {
            "plan_id": {"type": "integer", "minimum": 1},
            "mode": {
                "type": "string",
                "enum": ["preview", "apply"],
            },
            "instructions": {
                "type": "string",
                "minLength": 1,
                "maxLength": 4000,
            },
        },
    }

    async def handler(args: Dict[str, Any]) -> Dict[str, Any]:
        raw_plan_id = args.get("plan_id")
        if raw_plan_id is None:
            raise ValueError("plan_id is required")
        try:
            plan_id = int(raw_plan_id)
        except Exception as exc:  # pragma: no cover
            raise ValueError("plan_id must be an integer") from exc

        raw_mode = args.get("mode") or "apply"
        mode_str = str(raw_mode).lower()
        mode: Literal["preview", "apply"]
        if mode_str not in ("preview", "apply"):
            mode = "apply"
        else:
            mode = mode_str  # type: ignore[assignment]

        raw_instructions = args.get("instructions")
        if not isinstance(raw_instructions, str) or not raw_instructions.strip():
            raise ValueError("instructions must be a non-empty string")
        prompt_text = raw_instructions.strip()

        command = await generate_mass_edit_command(prompt_text, mode)
        plan = await apply_mass_edit_to_plan(plan_id, user_id, command)
        return {"plan": plan, "mass_edit_command": command}

    return ToolSpec(
        name="plan_mass_edit",
        description="Apply AI-powered mass edit to a user's calendar training plan.",
        parameters_schema=parameters_schema,
        handler=handler,
    )
