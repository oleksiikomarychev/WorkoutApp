"""Celery tasks responsible for training plan generation."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from celery import shared_task
from celery.utils.log import get_task_logger

from ..celery_app import PLAN_TASK_QUEUE
from ..dependencies import SessionLocal
from ..metrics import TRAINING_PLANS_GENERATED_TOTAL
from ..schemas.training_plans import TrainingPlan
from ..schemas.user_data import UserDataInput
from ..services.generated_plan_storage import save_generated_plan
from ..services.plan_generation import (
    generate_training_plan,
    generate_training_plan_with_rationale,
    generate_training_plan_with_summary,
)
from ..services.plans_service import save_plan_to_plans_service
from ..services.rpe_rpc import notify_rpe_plan_created

logger = get_task_logger(__name__)


def _run_async(coro):
    return asyncio.run(coro)


def _persist_plan(plan: TrainingPlan, user_id: str) -> None:
    db = SessionLocal()
    try:
        save_generated_plan(db, plan, user_id)
    finally:
        db.close()


def _notify_downstream(plan: TrainingPlan, user_id: str) -> None:
    try:
        _run_async(save_plan_to_plans_service(plan, user_id))
    except Exception as exc:  # pragma: no cover - best effort logging
        logger.warning("plans_service_notification_failed", exc_info=exc)
    try:
        _run_async(notify_rpe_plan_created(plan, user_id))
    except Exception as exc:  # pragma: no cover
        logger.warning("rpe_notification_failed", exc_info=exc)


def _build_payload(
    *,
    variant: str,
    plan: TrainingPlan,
    rationale: Optional[str] = None,
    summary: Optional[str] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "variant": variant,
        "plan": plan.model_dump(mode="json"),
    }
    if rationale is not None:
        payload["plan_rationale"] = rationale
    if summary is not None:
        payload["plan_summary"] = summary
    return payload


def _handle_success(plan: TrainingPlan, user_id: str, variant: str) -> None:
    _persist_plan(plan, user_id)
    _notify_downstream(plan, user_id)
    TRAINING_PLANS_GENERATED_TOTAL.labels(variant=variant).inc()


def _parse_user_data(data: Dict[str, Any]) -> UserDataInput:
    return UserDataInput.model_validate(data)


@shared_task(bind=True, name="agent.generate_plan", queue=PLAN_TASK_QUEUE, max_retries=3)
def generate_plan_task(self, user_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Generate base training plan."""
    try:
        plan = _run_async(generate_training_plan(_parse_user_data(user_data)))
        _handle_success(plan, user_id, "base")
        return _build_payload(variant="base", plan=plan)
    except Exception as exc:
        logger.exception("generate_plan_task_failed", exc_info=exc)
        raise self.retry(exc=exc, countdown=60)


@shared_task(
    bind=True,
    name="agent.generate_plan_with_rationale",
    queue=PLAN_TASK_QUEUE,
    max_retries=3,
)
def generate_plan_with_rationale_task(self, user_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Generate plan plus rationale."""
    try:
        plan, rationale = _run_async(generate_training_plan_with_rationale(_parse_user_data(user_data)))
        _handle_success(plan, user_id, "rationale")
        return _build_payload(variant="rationale", plan=plan, rationale=rationale)
    except Exception as exc:
        logger.exception("generate_plan_with_rationale_failed", exc_info=exc)
        raise self.retry(exc=exc, countdown=90)


@shared_task(
    bind=True,
    name="agent.generate_plan_with_summary",
    queue=PLAN_TASK_QUEUE,
    max_retries=3,
)
def generate_plan_with_summary_task(self, user_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Generate plan plus summary snippet."""
    try:
        plan, summary = _run_async(generate_training_plan_with_summary(_parse_user_data(user_data)))
        _handle_success(plan, user_id, "summary")
        return _build_payload(variant="summary", plan=plan, summary=summary)
    except Exception as exc:
        logger.exception("generate_plan_with_summary_failed", exc_info=exc)
        raise self.retry(exc=exc, countdown=90)
