import logging
from typing import Any

import httpx

from ..config import settings
from ..schemas.training_plans import TrainingPlan

logger = logging.getLogger(__name__)


async def notify_rpe_plan_created(plan: TrainingPlan) -> bool:
    """Send freshly generated plan to the RPE service for downstream processing."""
    url = f"{settings.rpe_service_url.rstrip('/')}/rpe/plans"
    payload: dict[str, Any] = {
        "plan": plan.model_dump(mode="json"),
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        logger.info("Notified RPE service about generated plan | status=%d", response.status_code)
        return True
    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        logger.warning("Failed to notify RPE service about generated plan: %s", exc)
        return False
