from typing import Any

import httpx
import structlog

from ..config import settings
from .tool_agent import ToolSpec

logger = structlog.get_logger(__name__)


def analyze_athlete_history_tool(user_id: str) -> ToolSpec:
    parameters_schema: dict[str, Any] = {
        "type": "object",
        "required": ["athlete_id"],
        "properties": {
            "athlete_id": {
                "type": "string",
                "description": "ID of the athlete whose history should be analyzed.",
            },
            "days": {
                "type": "integer",
                "default": 180,
                "description": (
                    "Number of days back to include in the analysis (e.g. 90, 180, 365). "
                    "Internally this is converted to weeks for the CRM analytics endpoint."
                ),
            },
        },
    }

    async def handler(args: dict[str, Any]) -> dict[str, Any]:
        athlete_id = args.get("athlete_id")
        if not athlete_id:
            return {"error": "athlete_id is required"}

        raw_days = args.get("days", 180)
        try:
            days = int(raw_days)
        except Exception:
            days = 180

        weeks = max(1, min(104, days // 7 or 1))

        base_url = settings.crm_service_url.rstrip("/")
        url = f"{base_url}/crm/analytics/athletes/{athlete_id}"
        headers = {"X-User-Id": user_id}
        params = {
            "weeks": weeks,
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                logger.info(
                    "fetching_athlete_history_analytics",
                    user_id=user_id,
                    athlete_id=athlete_id,
                    days=days,
                    weeks=weeks,
                    url=url,
                    params=params,
                )
                resp = await client.get(url, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                return {
                    "athlete_id": athlete_id,
                    "days": days,
                    "weeks": weeks,
                    "raw": data,
                }
            except Exception as exc:
                logger.error(
                    "failed_to_fetch_athlete_history_analytics",
                    user_id=user_id,
                    athlete_id=athlete_id,
                    error=str(exc),
                )
                return {"error": f"Failed to fetch athlete history analytics: {exc}"}

    return ToolSpec(
        name="analyze_athlete_history",
        description=(
            "Analyze a specific athlete's training history (for coaches). "
            "Use this when the user asks about one athlete's long-term trends, "
            "consistency, or workload over weeks or months."
        ),
        parameters_schema=parameters_schema,
        handler=handler,
    )
