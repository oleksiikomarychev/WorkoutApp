"""RPC client to notify RPE service about generated plans."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from ..config import settings
from ..schemas.training_plans import TrainingPlan

logger = structlog.get_logger(__name__)


async def notify_rpe_plan_created(plan: TrainingPlan, user_id: str) -> bool:
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
            "notified_rpe_plan_created",
            user_id=user_id,
            status_code=response.status_code,
        )
        return True
    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        logger.warning("failed_to_notify_rpe_service", user_id=user_id, error=str(exc))
        return False
    except Exception as exc:
        logger.warning("failed_to_notify_rpe_service_unexpected", user_id=user_id, error=str(exc))
        return False
