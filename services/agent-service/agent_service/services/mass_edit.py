from typing import Any, Dict, List, Literal

import httpx
import structlog
from fastapi import HTTPException, status

from ..config import settings
from ..metrics import (
    MASS_EDIT_APPLICATIONS_TOTAL,
    MASS_EDIT_COMMANDS_REQUESTED_TOTAL,
)
from ..prompts.mass_edit import (
    APPLIED_MASS_EDIT_PROMPT_TEMPLATE,
    MASS_EDIT_PROMPT_TEMPLATE,
)
from .entity_resolver import build_applied_mass_edit_filter_hints, parse_inline_references
from .llm_wrapper import generate_structured_output
from .tool_agent import ToolSpec

logger = structlog.get_logger(__name__)

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


APPLIED_MASS_EDIT_COMMAND_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["filter", "actions"],
    "properties": {
        "mode": {
            "type": "string",
            "enum": ["preview", "apply"],
        },
        "filter": {
            "type": "object",
            "properties": {
                "plan_order_indices": {
                    "type": "array",
                    "items": {"type": "integer", "minimum": 0},
                },
                "from_order_index": {"type": "integer", "minimum": 0},
                "to_order_index": {"type": "integer", "minimum": 0},
                "only_future": {"type": "boolean"},
                "scheduled_from": {"type": "string"},
                "scheduled_to": {"type": "string"},
                "status_in": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "exercise_definition_ids": {
                    "type": "array",
                    "items": {"type": "integer", "minimum": 1},
                },
                # Set-level filters
                "intensity_lte": {"type": "number"},
                "intensity_gte": {"type": "number"},
                "volume_lte": {"type": "integer", "minimum": 0},
                "volume_gte": {"type": "integer", "minimum": 0},
                "weight_lte": {"type": "number", "minimum": 0},
                "weight_gte": {"type": "number", "minimum": 0},
                "effort_lte": {"type": "number"},
                "effort_gte": {"type": "number"},
            },
        },
        "actions": {
            "type": "object",
            "properties": {
                "set_intensity": {"type": "number"},
                "increase_intensity_by": {"type": "number"},
                "decrease_intensity_by": {"type": "number"},
                "set_volume": {"type": "integer", "minimum": 1},
                "increase_volume_by": {"type": "integer"},
                "decrease_volume_by": {"type": "integer"},
                "set_weight": {"type": "number", "minimum": 0},
                "increase_weight_by": {"type": "number"},
                "decrease_weight_by": {"type": "number"},
                "set_effort": {"type": "number"},
                "increase_effort_by": {"type": "number"},
                "decrease_effort_by": {"type": "number"},
                "clamp_non_negative": {"type": "boolean"},
                "replace_exercise_definition_id_to": {"type": "integer", "minimum": 1},
                "replace_exercise_name_to": {"type": "string"},
                "add_exercise_instances": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["exercise_definition_id"],
                        "properties": {
                            "exercise_definition_id": {
                                "type": "integer",
                                "minimum": 1,
                                "description": "Exercise definition (exercise_list) id to add",
                            },
                            "notes": {"type": "string"},
                            "order": {"type": "integer", "minimum": 0},
                            "sets": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "volume": {"type": "integer", "minimum": 1},
                                        "intensity": {"type": "number"},
                                        "weight": {"type": "number", "minimum": 0},
                                        "effort": {"type": "number"},
                                    },
                                },
                            },
                        },
                    },
                },
            },
        },
    },
}


async def generate_mass_edit_command(prompt: str, desired_mode: Literal["preview", "apply"]) -> Dict[str, Any]:
    """Call the LLM to transform a natural-language request into PlanMassEditCommand JSON."""

    composed_prompt = MASS_EDIT_PROMPT_TEMPLATE.format(user_prompt=f"User request: {prompt}")
    logger.info(
        "mass_edit_command_generate_requested",
        prompt=prompt,
        mode=desired_mode,
    )
    MASS_EDIT_COMMANDS_REQUESTED_TOTAL.inc()
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
        logger.error(
            "mass_edit_command_invalid",
            reason="missing_filter_or_actions",
            command=command,
        )
        raise ValueError("LLM response missing required keys 'filter' or 'actions'")

    logger.info(
        "mass_edit_command_generated",
        mode=desired_mode,
        has_filter="filter" in command,
        has_actions="actions" in command,
    )
    return command


async def fetch_exercise_definitions() -> str:
    """Fetch all exercise definitions to provide context for the LLM."""
    base_url = settings.exercises_service_url
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            url = f"{base_url.rstrip('/')}/exercises/definitions/"
            resp = await client.get(url)
            resp.raise_for_status()
            defs = resp.json()
            lines = []
            for item in defs:
                lines.append(f"- {item.get('name')} (ID: {item.get('id')})")
            return "\n".join(lines)
    except Exception as exc:
        logger.warning("failed_to_fetch_exercises_context", error=str(exc))
        return ""


async def generate_applied_mass_edit_command(prompt: str, desired_mode: Literal["preview", "apply"]) -> Dict[str, Any]:
    """Call the LLM to transform a natural-language request into AppliedPlanMassEditCommand JSON."""

    exercises_context = await fetch_exercise_definitions()
    context_str = ""
    if exercises_context:
        context_str = f"\nAvailable Exercises (Use these IDs):\n{exercises_context}\n"

    composed_prompt = APPLIED_MASS_EDIT_PROMPT_TEMPLATE.format(user_prompt=f"User request: {prompt}\n{context_str}")
    logger.info(
        "applied_mass_edit_command_generate_requested",
        prompt=prompt,
        mode=desired_mode,
    )
    MASS_EDIT_COMMANDS_REQUESTED_TOTAL.inc()
    command = await generate_structured_output(
        prompt=composed_prompt,
        response_schema=APPLIED_MASS_EDIT_COMMAND_SCHEMA,
        temperature=0.2,
        max_output_tokens=2048,
    )

    if not isinstance(command, dict):
        raise ValueError("LLM response is not a JSON object")

    command.setdefault("mode", desired_mode)

    if "filter" not in command or "actions" not in command:
        logger.error(
            "applied_mass_edit_command_invalid",
            reason="missing_filter_or_actions",
            command=command,
        )
        raise ValueError("LLM response missing required keys 'filter' or 'actions'")

    # Safety: AppliedPlanExerciseFilter in workouts-service requires at least one
    # scope field among plan_order_indices, from/to_order_index, or
    # scheduled_from/scheduled_to. If the LLM omitted all of them, default to
    # "all relevant future workouts in this applied plan" by setting
    # from_order_index = 0 and only_future = true.
    flt = command.get("filter")
    if isinstance(flt, dict):
        plan_order_indices = flt.get("plan_order_indices")
        from_idx = flt.get("from_order_index")
        to_idx = flt.get("to_order_index")
        scheduled_from = flt.get("scheduled_from")
        scheduled_to = flt.get("scheduled_to")

        if (
            plan_order_indices is None
            and from_idx is None
            and to_idx is None
            and scheduled_from is None
            and scheduled_to is None
        ):
            flt.setdefault("from_order_index", 0)
            flt.setdefault("only_future", True)
            command["filter"] = flt
            logger.info(
                "applied_mass_edit_filter_scope_defaulted",
                filter=flt,
            )

    logger.info(
        "applied_mass_edit_command_generated",
        mode=desired_mode,
        has_filter="filter" in command,
        has_actions="actions" in command,
    )
    return command


async def apply_mass_edit_to_plan(plan_id: int, user_id: str, command: Dict[str, Any]) -> Dict[str, Any]:
    """Proxy the generated command to plans-service and return the updated plan."""

    url = f"{settings.plans_service_url}/plans/calendar-plans/{plan_id}/mass-edit"
    headers = {"X-User-Id": user_id}

    logger.info(
        "mass_edit_apply_requested",
        user_id=user_id,
        plan_id=plan_id,
        mode=command.get("mode"),
        operation=command.get("operation"),
    )
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, json=command, headers=headers)
            response.raise_for_status()
            body = response.json()
            logger.info(
                "mass_edit_apply_success",
                user_id=user_id,
                plan_id=plan_id,
            )
            MASS_EDIT_APPLICATIONS_TOTAL.inc()
            return body
    except httpx.HTTPStatusError as exc:
        detail = (
            exc.response.json()
            if exc.response.headers.get("content-type", "").startswith("application/json")
            else exc.response.text
        )
        logger.warning(
            "mass_edit_apply_http_error",
            user_id=user_id,
            plan_id=plan_id,
            status_code=exc.response.status_code,
            detail=detail,
        )
        raise HTTPException(status_code=exc.response.status_code, detail=detail)
    except httpx.RequestError as exc:
        logger.error(
            "mass_edit_apply_request_failed",
            user_id=user_id,
            plan_id=plan_id,
            error=str(exc),
        )
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Plans service unavailable")


async def apply_applied_mass_edit_to_plan(
    applied_plan_id: int,
    user_id: str,
    command: Dict[str, Any],
) -> Dict[str, Any]:
    """Proxy the generated applied mass-edit command to workouts-service.

    Returns the summary response from workouts-service.
    """

    url = f"{settings.workouts_service_url}/workouts/applied-plans/{applied_plan_id}/mass-edit-sets"
    headers = {"X-User-Id": user_id}

    logger.info(
        "applied_mass_edit_apply_requested",
        user_id=user_id,
        applied_plan_id=applied_plan_id,
        mode=command.get("mode"),
    )
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=command, headers=headers)
            response.raise_for_status()
            body = response.json()
            logger.info(
                "applied_mass_edit_apply_success",
                user_id=user_id,
                applied_plan_id=applied_plan_id,
            )
            MASS_EDIT_APPLICATIONS_TOTAL.inc()
            return body
    except httpx.HTTPStatusError as exc:
        detail = (
            exc.response.json()
            if exc.response.headers.get("content-type", "").startswith("application/json")
            else exc.response.text
        )
        logger.warning(
            "applied_mass_edit_apply_http_error",
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            status_code=exc.response.status_code,
            detail=detail,
        )
        raise HTTPException(status_code=exc.response.status_code, detail=detail)
    except httpx.RequestError as exc:
        logger.error(
            "applied_mass_edit_apply_request_failed",
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            error=str(exc),
        )
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Workouts service unavailable")


async def shift_applied_plan_schedule(
    applied_plan_id: int,
    user_id: str,
    from_date: str,
    days: int = 0,
    to_date: str | None = None,
    new_rest_days: int | None = None,
    add_rest_every_n_workouts: int | None = None,
    add_rest_at_indices: List[int] | None = None,
    add_rest_days_amount: int = 1,
    action_type: Literal["shift", "set_rest"] = "shift",
    only_future: bool = False,
    status_in: List[str] | None = None,
    mode: Literal["preview", "apply"] = "apply",
) -> Dict[str, Any]:
    """Proxy schedule-shift command to workouts-service for an applied plan.

    This is a thin wrapper around the workouts-service endpoint
    /workouts/applied-plans/{applied_plan_id}/shift-schedule.
    """

    url = f"{settings.workouts_service_url}/workouts/applied-plans/{applied_plan_id}/shift-schedule"
    headers = {"X-User-Id": user_id}
    payload: Dict[str, Any] = {
        "from_date": from_date,
        "to_date": to_date,
        "days": days,
        "new_rest_days": new_rest_days,
        "add_rest_every_n_workouts": add_rest_every_n_workouts,
        "add_rest_at_indices": add_rest_at_indices,
        "add_rest_days_amount": add_rest_days_amount,
        "action_type": action_type,
        "only_future": only_future,
        "status_in": status_in,
        "mode": mode,
    }

    logger.info(
        "applied_schedule_shift_apply_requested",
        user_id=user_id,
        applied_plan_id=applied_plan_id,
        from_date=from_date,
        to_date=to_date,
        days=days,
        new_rest_days=new_rest_days,
        add_rest_every_n_workouts=add_rest_every_n_workouts,
        action_type=action_type,
        only_future=only_future,
        status_in=status_in,
    )
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            body = response.json()
            logger.info(
                "applied_schedule_shift_apply_success",
                user_id=user_id,
                applied_plan_id=applied_plan_id,
                days=days,
                action_type=action_type,
            )
            return body
    except httpx.HTTPStatusError as exc:
        detail = (
            exc.response.json()
            if exc.response.headers.get("content-type", "").startswith("application/json")
            else exc.response.text
        )
        logger.warning(
            "applied_schedule_shift_apply_http_error",
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            status_code=exc.response.status_code,
            detail=detail,
        )
        raise HTTPException(status_code=exc.response.status_code, detail=detail)
    except httpx.RequestError as exc:
        logger.error(
            "applied_schedule_shift_apply_request_failed",
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            error=str(exc),
        )
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Workouts service unavailable")


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

        # For ActivePlanScreen tool usage we always want to perform real
        # modifications, not just a preview, so we force mode="apply"
        # regardless of what the LLM passed in arguments.
        mode: Literal["preview", "apply"] = "apply"

        raw_instructions = args.get("instructions")
        if not isinstance(raw_instructions, str) or not raw_instructions.strip():
            raise ValueError("instructions must be a non-empty string")
        prompt_text = raw_instructions.strip()

        logger.info(
            "mass_edit_tool_invocation",
            user_id=user_id,
            plan_id=plan_id,
            mode=mode,
        )
        command = await generate_mass_edit_command(prompt_text, mode)
        plan = await apply_mass_edit_to_plan(plan_id, user_id, command)
        logger.info(
            "mass_edit_tool_success",
            user_id=user_id,
            plan_id=plan_id,
            mode=mode,
        )
        return {"plan": plan, "mass_edit_command": command}

    return ToolSpec(
        name="plan_mass_edit",
        description="Apply AI-powered mass edit to a user's calendar training plan.",
        parameters_schema=parameters_schema,
        handler=handler,
    )


def create_applied_plan_mass_edit_tool(user_id: str) -> ToolSpec:
    """ToolSpec for applying mass edits to an applied plan using natural language instructions."""

    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "required": ["applied_plan_id", "instructions"],
        "properties": {
            "applied_plan_id": {"type": "integer", "minimum": 1},
            "mode": {
                "type": "string",
                "enum": ["preview", "apply"],
                "description": (
                    "Optional mode. Defaults to 'preview' for safety. "
                    "Use 'apply' only if the user explicitly confirms or asks "
                    "to execute changes immediately."
                ),
            },
            "instructions": {
                "type": "string",
                "minLength": 1,
                "maxLength": 4000,
                "description": (
                    "Natural language instructions for editing the plan (e.g., " "'Replace squat with leg press')"
                ),
            },
        },
    }

    async def handler(args: Dict[str, Any]) -> Dict[str, Any]:
        raw_applied_plan_id = args.get("applied_plan_id")
        if raw_applied_plan_id is None:
            raise ValueError("applied_plan_id is required")
        try:
            applied_plan_id = int(raw_applied_plan_id)
        except Exception as exc:  # pragma: no cover
            raise ValueError("applied_plan_id must be an integer") from exc

        # Default to 'preview' if not specified, unless the LLM explicitly chose 'apply'.
        raw_mode = args.get("mode")
        if not raw_mode:
            mode: Literal["preview", "apply"] = "preview"
        else:
            mode_str = str(raw_mode).lower()
            if mode_str not in ("preview", "apply"):
                mode = "preview"
            else:
                mode = mode_str  # type: ignore[assignment]

        raw_instructions = args.get("instructions")
        if not isinstance(raw_instructions, str) or not raw_instructions.strip():
            raise ValueError("instructions must be a non-empty string")
        prompt_text = raw_instructions.strip()

        logger.info(
            "applied_mass_edit_tool_invocation",
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            mode=mode,
        )
        inline_refs = parse_inline_references(prompt_text)
        filter_hints: Dict[str, Any] = {}
        if inline_refs:
            filter_hints = await build_applied_mass_edit_filter_hints(
                inline_refs,
                active_applied_plan_id=applied_plan_id,
            )

        command = await generate_applied_mass_edit_command(prompt_text, mode)

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

        # Ensure the command mode matches the decided mode (preview/apply).
        command["mode"] = mode
        result = await apply_applied_mass_edit_to_plan(applied_plan_id, user_id, command)
        logger.info(
            "applied_mass_edit_tool_success",
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            mode=mode,
        )
        # Return instructions so the frontend can later trigger an explicit
        # "apply" run using the same natural-language request, if needed.
        return {"summary": result, "mass_edit_command": command, "instructions": prompt_text}

    return ToolSpec(
        name="applied_plan_mass_edit",
        description=(
            "Apply AI-powered mass edit to a user's ACTIVE applied training plan "
            "(modifies exercises, sets, volumes, etc.)."
        ),
        parameters_schema=parameters_schema,
        handler=handler,
    )


def create_applied_plan_schedule_shift_tool(user_id: str) -> ToolSpec:
    """ToolSpec для сдвига или реструктуризации расписания applied-плана."""

    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "required": ["applied_plan_id", "from_date"],
        "properties": {
            "applied_plan_id": {"type": "integer", "minimum": 1},
            "from_date": {
                "type": "string",
                "description": (
                    "ISO-дата (YYYY-MM-DD или полная дата-время), начиная с которой нужно " "менять расписание."
                ),
            },
            "to_date": {
                "type": "string",
                "description": (
                    "ISO-дата окончания интервала (включительно). Если не указана, применяется до конца плана."
                ),
            },
            "days": {
                "type": "integer",
                "default": 0,
                "description": (
                    "На сколько дней сдвинуть расписание (для режима 'shift'). " "Может быть отрицательным."
                ),
            },
            "new_rest_days": {
                "type": "integer",
                "minimum": 0,
                "description": (
                    "Новое количество дней отдыха между тренировками (для режима 'set_rest'). "
                    "Например, 1 день отдыха = 2 дня между тренировками."
                ),
            },
            "action_type": {
                "type": "string",
                "enum": ["shift", "set_rest"],
                "default": "shift",
                "description": "Тип операции: 'shift' (простой сдвиг) или 'set_rest' (изменение интервалов)",
            },
            "add_rest_every_n_workouts": {
                "type": "integer",
                "minimum": 1,
                "description": (
                    "Добавлять день отдыха после каждой N-й тренировки "
                    "(циклический паттерн). Например, 4 = после каждой 4-й тренировки."
                ),
            },
            "add_rest_at_indices": {
                "type": "array",
                "items": {"type": "integer", "minimum": 1},
                "description": (
                    "Список порядковых номеров (1-based) тренировок, после " "которых нужно добавить день отдыха."
                ),
            },
            "add_rest_days_amount": {
                "type": "integer",
                "minimum": 1,
                "default": 1,
                "description": "Сколько дней отдыха добавлять при срабатывании паттерна (по умолчанию 1).",
            },
            "only_future": {
                "type": "boolean",
                "default": False,
                "description": "Если true, менять только будущие тренировки",
            },
            "status_in": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Необязательный список статусов тренировок для изменения",
            },
            "mode": {
                "type": "string",
                "enum": ["preview", "apply"],
            },
        },
    }

    async def handler(args: Dict[str, Any]) -> Dict[str, Any]:
        raw_applied_plan_id = args.get("applied_plan_id")
        if raw_applied_plan_id is None:
            raise ValueError("applied_plan_id is required")
        try:
            applied_plan_id = int(raw_applied_plan_id)
        except Exception as exc:  # pragma: no cover
            raise ValueError("applied_plan_id must be an integer") from exc

        from_date_val = str(args.get("from_date") or "").strip()
        if not from_date_val:
            raise ValueError("from_date must be a non-empty ISO date string")

        to_date_val = args.get("to_date")
        if to_date_val is not None:
            to_date_val = str(to_date_val).strip() or None

        days_val = args.get("days", 0)
        try:
            days = int(days_val)
        except Exception as exc:
            raise ValueError("days must be an integer") from exc

        new_rest_days = args.get("new_rest_days")
        if new_rest_days is not None:
            try:
                new_rest_days = int(new_rest_days)
            except Exception as exc:
                raise ValueError("new_rest_days must be an integer") from exc

        add_rest_every_n_workouts = args.get("add_rest_every_n_workouts")
        if add_rest_every_n_workouts is not None:
            try:
                add_rest_every_n_workouts = int(add_rest_every_n_workouts)
            except Exception as exc:
                raise ValueError("add_rest_every_n_workouts must be an integer") from exc

        add_rest_at_indices = args.get("add_rest_at_indices")
        if add_rest_at_indices is not None and not isinstance(add_rest_at_indices, list):
            raise ValueError("add_rest_at_indices must be a list of integers")

        add_rest_days_amount = args.get("add_rest_days_amount", 1)
        try:
            add_rest_days_amount = int(add_rest_days_amount)
        except Exception as exc:
            raise ValueError("add_rest_days_amount must be an integer") from exc

        action_type = args.get("action_type", "shift")
        if action_type not in ("shift", "set_rest"):
            action_type = "shift"

        # Safety: if the model passed a "rest interval" parameter but kept
        # action_type="shift" and days=0, treat this as a request to
        # restructure gaps between workouts rather than a no-op shift.
        if action_type == "shift" and new_rest_days is not None and days == 0:
            action_type = "set_rest"

        only_future = bool(args.get("only_future", False))
        status_in = args.get("status_in")
        if status_in is not None and not isinstance(status_in, list):
            raise ValueError("status_in must be a list of strings or null")

        raw_mode = args.get("mode")
        if not raw_mode:
            mode: Literal["preview", "apply"] = "preview"
        else:
            mode_str = str(raw_mode).lower()
            if mode_str not in ("preview", "apply"):
                mode = "preview"
            else:
                mode = mode_str  # type: ignore[assignment]

        logger.info(
            "applied_schedule_shift_tool_invocation",
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            from_date=from_date_val,
            to_date=to_date_val,
            days=days,
            new_rest_days=new_rest_days,
            add_rest_every_n_workouts=add_rest_every_n_workouts,
            add_rest_at_indices=add_rest_at_indices,
            add_rest_days_amount=add_rest_days_amount,
            action_type=action_type,
            only_future=only_future,
            status_in=status_in,
        )

        # Build a deterministic command payload that captures all parameters
        # used for this schedule shift. This is returned to the frontend so it
        # can render a structured card and, in the future, re-apply the exact
        # same command without involving the LLM again.
        command: Dict[str, Any] = {
            "from_date": from_date_val,
            "to_date": to_date_val,
            "days": days,
            "new_rest_days": new_rest_days,
            "add_rest_every_n_workouts": add_rest_every_n_workouts,
            "add_rest_at_indices": add_rest_at_indices,
            "add_rest_days_amount": add_rest_days_amount,
            "action_type": action_type,
            "only_future": only_future,
            "status_in": status_in,
        }

        # We need to update shift_applied_plan_schedule signature or pass kwargs?
        # shift_applied_plan_schedule is a wrapper around POST request.
        # It constructs the payload manually. We need to update it too.
        summary = await shift_applied_plan_schedule(
            applied_plan_id=applied_plan_id,
            user_id=user_id,
            from_date=from_date_val,
            to_date=to_date_val,
            days=days,
            new_rest_days=new_rest_days,
            # Pass new params as kwargs to be forwarded
            add_rest_every_n_workouts=add_rest_every_n_workouts,
            add_rest_at_indices=add_rest_at_indices,
            add_rest_days_amount=add_rest_days_amount,
            action_type=action_type,
            only_future=only_future,
            status_in=status_in,
            mode=mode,
        )
        logger.info(
            "applied_schedule_shift_tool_success",
            user_id=user_id,
            applied_plan_id=applied_plan_id,
            days=days,
            action_type=action_type,
        )
        return {"summary": summary, "schedule_shift_command": command, "mode": mode}

    return ToolSpec(
        name="applied_plan_schedule_shift",
        description=(
            "Manage the schedule of an applied training plan. Supports shifting workouts by N days, "
            "changing rest intervals, or inserting extra rest days periodically (e.g. after every 4th workout)."
        ),
        parameters_schema=parameters_schema,
        handler=handler,
    )


def create_exercise_lookup_tool(
    *,
    user_id: str,
    context_exercises: List[Dict[str, Any]] | None = None,
) -> ToolSpec:
    """Tool that resolves user-facing exercise names to exercise_definition_id.

    It first tries to match against exercises present in the current plan
    ("plan_exercises" from structured context), then falls back to
    querying exercises-service /exercises/definitions.
    """

    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "required": ["query"],
        "properties": {
            "query": {
                "type": "string",
                "minLength": 1,
                "description": "User-facing exercise name or phrase, e.g. 'присед', 'жим лежа'.",
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "default": 5,
            },
            "must_be_in_plan": {
                "type": "boolean",
                "description": "If true, restrict results to exercises already present in the current applied plan.",
                "default": True,
            },
        },
    }

    async def handler(args: Dict[str, Any]) -> Dict[str, Any]:
        query = str(args.get("query") or "").strip()
        if not query:
            raise ValueError("query must be a non-empty string")

        limit = int(args.get("limit") or 5)
        must_be_in_plan = bool(args.get("must_be_in_plan", True))

        results: List[Dict[str, Any]] = []

        # 1) Try to match against exercises from the current plan, if provided.
        plan_exercises = context_exercises or []
        if plan_exercises:
            q_lower = query.lower()
            for ex in plan_exercises:
                name = str(ex.get("name") or "")
                norm = str(ex.get("normalized_name") or name).lower()
                aliases = ex.get("aliases") or []
                aliases_lower = [str(a).lower() for a in aliases]
                if q_lower in norm or any(q_lower in a for a in aliases_lower) or q_lower == norm:
                    results.append(
                        {
                            "exercise_definition_id": ex.get("exercise_definition_id"),
                            "name": name,
                            "normalized_name": norm,
                            "aliases": aliases,
                            "in_current_plan": True,
                        }
                    )
            if must_be_in_plan and results:
                return {"items": results[:limit]}

        # 2) Fallback: query exercises-service for definitions
        base_url = settings.exercises_service_url
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # For now, we reuse the definitions listing endpoint and filter client-side.
                url = f"{base_url.rstrip('/')}/exercises/definitions"
                resp = await client.get(url)
                resp.raise_for_status()
                defs = resp.json()
        except Exception as exc:  # pragma: no cover - best-effort lookup
            logger.warning("exercise_lookup_remote_failed", error=str(exc))
            return {"items": results[:limit]}

        q_lower = query.lower()
        for item in defs:
            name = str(item.get("name") or "")
            norm = name.lower()
            if q_lower in norm or q_lower == norm:
                results.append(
                    {
                        "exercise_definition_id": item.get("id"),
                        "name": name,
                        "normalized_name": norm,
                        "aliases": [],
                        "in_current_plan": False,
                    }
                )

        return {"items": results[:limit]}

    return ToolSpec(
        name="exercise_lookup",
        description=(
            "Lookup exercise definitions by user-facing name and return candidate "
            "exercise_definition_id values, preferring exercises present in the current plan."
        ),
        parameters_schema=parameters_schema,
        handler=handler,
    )
