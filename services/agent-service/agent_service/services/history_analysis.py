from typing import Any

import httpx
import structlog

from ..config import settings
from .tool_agent import ToolSpec

logger = structlog.get_logger(__name__)


def analyze_completed_workouts_tool(user_id: str) -> ToolSpec:
    async def handler(args: dict[str, Any]) -> dict[str, Any]:
        days = args.get("days", 30)

        base_url = settings.workouts_service_url.rstrip("/")
        url = f"{base_url}/workouts/analytics/completed"
        headers = {"X-User-Id": user_id}
        params = {"days": days}

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                logger.info("fetching_completed_workouts_analytics", user_id=user_id, days=days)
                resp = await client.get(url, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()

                items = data.get("items", [])

                if not items:
                    return {"summary": f"No completed workouts found in the last {days} days."}

                total_workouts = len(items)
                total_volume = sum(item["metrics"]["volume_sum"] for item in items)
                avg_intensity = (
                    sum(item["metrics"]["intensity_avg"] for item in items) / total_workouts if total_workouts else 0
                )

                return {
                    "period_days": days,
                    "total_workouts": total_workouts,
                    "total_volume": total_volume,
                    "avg_intensity": avg_intensity,
                    "workouts_per_week": round(total_workouts / (days / 7), 2),
                    "details": items,
                }

            except Exception as e:
                logger.error("failed_to_fetch_completed_workouts_analytics", error=str(e))
                return {"error": f"Failed to fetch analysis: {str(e)}"}

    return ToolSpec(
        name="analyze_completed_workouts",
        description=(
            "Analyze the user's completed workout history (volume, intensity, frequency) over a period. "
            "Use this to identify training trends, consistency, and overall progress."
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "days": {"type": "integer", "default": 30, "description": "Number of days to analyze (e.g. 30, 90)."}
            },
        },
        handler=handler,
    )
