import logging
from typing import Any

import httpx

from ..config import settings
from ..schemas.training_plans import TrainingPlan

logger = logging.getLogger(__name__)


async def notify_rpe_plan_created(plan: TrainingPlan, user_id: str) -> bool:
    """Send freshly generated plan to the RPE service for downstream processing."""
    url = f"{settings.rpe_service_url.rstrip('/')}/rpe/plans"
    payload: dict[str, Any] = {
        "plan": plan.model_dump(mode="json"),
    }
    headers = {"X-User-Id": user_id}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
        logger.info(
            "Notified RPE service about generated plan for user %s | status=%d",
            user_id,
            response.status_code,
        )
        return True
    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        logger.warning("Failed to notify RPE service about generated plan: %s", exc)
        return False
