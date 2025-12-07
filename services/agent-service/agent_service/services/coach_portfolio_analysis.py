from typing import Any

import httpx
import structlog

from ..config import settings
from .tool_agent import ToolSpec

logger = structlog.get_logger(__name__)


def analyze_coach_athletes_portfolio_tool(user_id: str) -> ToolSpec:
    parameters_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "segment_filter": {
                "type": ["string", "null"],
                "description": (
                    "Optional segment to focus on, e.g. 'top_performer', "
                    "'on_track', 'at_risk', or 'new'. If null, all segments are included."
                ),
            },
            "min_sessions_per_week": {
                "type": "number",
                "default": 0,
                "description": "Minimum sessions per week filter (e.g. 1.5).",
            },
            "min_plan_adherence": {
                "type": "number",
                "default": 0.0,
                "description": "Minimum plan adherence filter in [0, 1] (e.g. 0.7 for 70%).",
            },
            "sort": {
                "type": "string",
                "default": "recently_active",
                "description": ("Sort key: 'recently_active', 'sessions_per_week', or 'plan_adherence'."),
            },
            "days": {
                "type": "integer",
                "default": 90,
                "description": "Number of days back to include in aggregated analytics.",
            },
        },
    }

    async def handler(args: dict[str, Any]) -> dict[str, Any]:
        segment_filter = args.get("segment_filter")
        min_sessions = args.get("min_sessions_per_week", 0)
        min_adherence = args.get("min_plan_adherence", 0.0)
        sort = args.get("sort") or "recently_active"
        raw_days = args.get("days", 90)
        try:
            days = int(raw_days)
        except Exception:
            days = 90

        weeks = max(1, min(104, days // 7 or 1))

        base_url = settings.crm_service_url.rstrip("/")
        url = f"{base_url}/crm/analytics/coaches/my/athletes"
        headers = {"X-User-Id": user_id}

        request_params: dict[str, Any] = {
            "weeks": weeks,
        }

        filters: dict[str, Any] = {
            "segment_filter": segment_filter,
            "min_sessions_per_week": min_sessions,
            "min_plan_adherence": min_adherence,
            "sort": sort,
            "days": days,
            "weeks": weeks,
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                logger.info(
                    "fetching_coach_athletes_portfolio",
                    user_id=user_id,
                    url=url,
                    params=request_params,
                    filters=filters,
                )
                resp = await client.get(url, params=request_params, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                return {
                    "filters": filters,
                    "raw": data,
                }
            except Exception as exc:
                logger.error(
                    "failed_to_fetch_coach_athletes_portfolio",
                    user_id=user_id,
                    error=str(exc),
                )
                return {"error": f"Failed to fetch coach athletes portfolio analytics: {exc}"}

    return ToolSpec(
        name="analyze_coach_athletes_portfolio",
        description=(
            "Analyze the coach's portfolio of athletes using aggregated analytics. "
            "Use this to answer questions about which athletes or segments to "
            "prioritize, who is at risk, and how different groups compare."
        ),
        parameters_schema=parameters_schema,
        handler=handler,
    )
