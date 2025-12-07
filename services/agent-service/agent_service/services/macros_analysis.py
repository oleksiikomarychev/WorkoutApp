from typing import Any

import httpx
import structlog

from ..config import settings
from .tool_agent import ToolSpec

logger = structlog.get_logger(__name__)


async def fetch_plan_macros(calendar_plan_id: int, user_id: str) -> list[dict[str, Any]]:
    url = f"{settings.plans_service_url}/plans/calendar-plans/{calendar_plan_id}/macros/"
    headers = {"X-User-Id": user_id}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code == 404:
            raise ValueError(f"Calendar plan {calendar_plan_id} not found")
        resp.raise_for_status()
        return resp.json()


def format_macros_definitions(macros: list[dict[str, Any]]) -> dict[str, Any]:
    if not macros:
        return {"count": 0, "message": "No macros (automation rules) found for this plan."}

    summary = {"count": len(macros), "macros": []}

    for m in macros:
        rule = m.get("rule", {})
        trigger = rule.get("trigger", {})
        condition = rule.get("condition", {})
        action = rule.get("action", {})

        macro_info = {
            "name": m.get("name", "Unnamed"),
            "active": m.get("is_active", True),
            "priority": m.get("priority", 100),
            "trigger_metric": trigger.get("metric"),
            "condition_op": condition.get("op"),
            "condition_val": condition.get("value") or condition.get("range") or condition.get("n"),
            "action_type": action.get("type"),
            "action_params": action.get("params"),
        }
        summary["macros"].append(macro_info)

    return summary


def create_macros_analysis_tool(user_id: str) -> ToolSpec:
    parameters_schema = {
        "type": "object",
        "required": ["calendar_plan_id"],
        "properties": {
            "calendar_plan_id": {
                "type": "integer",
                "description": "ID of the calendar plan (template) to analyze macros for",
            }
        },
    }

    async def handler(args: dict[str, Any]) -> dict[str, Any]:
        calendar_plan_id = args.get("calendar_plan_id")
        if not calendar_plan_id:
            raise ValueError("calendar_plan_id is required")

        try:
            macros_list = await fetch_plan_macros(int(calendar_plan_id), user_id)
            return format_macros_definitions(macros_list)
        except Exception as exc:
            logger.error("fetch_macros_failed", error=str(exc))
            return {"error": f"Failed to fetch plan macros: {str(exc)}"}

    return ToolSpec(
        name="analyze_plan_macros",
        description="Retrieve and explain the automation macros (rules) attached to this plan template.",
        parameters_schema=parameters_schema,
        handler=handler,
    )
