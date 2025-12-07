from typing import Any

import httpx
import structlog

from ..config import settings
from .tool_agent import ToolSpec

logger = structlog.get_logger(__name__)


def analyze_user_max_tool(user_id: str) -> ToolSpec:
    async def handler(args: dict[str, Any]) -> dict[str, Any]:
        recent_days = args.get("recent_days", 180)
        min_records = args.get("min_records", 1)
        synergist_weight = args.get("synergist_weight", 0.25)

        params = {
            "recent_days": recent_days,
            "min_records": min_records,
            "synergist_weight": synergist_weight,
            "use_llm": True,
            "fresh": True,
        }

        url = f"{settings.user_max_service_url.rstrip('/')}/user-max/analysis/weak-muscles"
        headers = {"X-User-Id": user_id}

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                logger.info("fetching_user_max_analysis", user_id=user_id, url=url, params=params)
                resp = await client.get(url, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                return data
            except Exception as e:
                logger.error("failed_to_fetch_user_max_analysis", error=str(e))
                return {"error": f"Failed to fetch analysis: {str(e)}"}

    return ToolSpec(
        name="analyze_user_max_data",
        description=(
            "Fetch and analyze the user's strength data, including identifying weak muscles, "
            "strength trends, and detecting anomalies in their records. "
            "Returns a JSON object with 'weak_muscles' (list), 'anomalies' (list of indices), "
            "and 'trend' (dictionary)."
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "recent_days": {
                    "type": "integer",
                    "default": 180,
                    "description": "Number of days to look back for analysis.",
                },
                "min_records": {
                    "type": "integer",
                    "default": 1,
                    "description": "Minimum records required per exercise.",
                },
                "synergist_weight": {
                    "type": "number",
                    "default": 0.25,
                    "description": "Weight factor for synergist muscles (0.0 to 1.0).",
                },
            },
        },
        handler=handler,
    )
