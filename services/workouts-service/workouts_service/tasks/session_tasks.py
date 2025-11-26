from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..celery_app import DEFAULT_QUEUE
from ..database import AsyncSessionLocal
from ..models import Workout, WorkoutExercise
from ..services.session_service import SessionService

logger = get_task_logger(__name__)


def _run_async(coro):
    return asyncio.run(coro)


async def _finish_session_postprocess_async(session_id: int, user_id: str) -> Dict[str, Any]:
    async with AsyncSessionLocal() as db:
        service = SessionService(db, user_id=user_id)

        session = await service.get_session_by_id(session_id)
        if not session:
            logger.warning("finish_session_postprocess_session_missing", session_id=session_id, user_id=user_id)
            return {"ok": False, "reason": "session_not_found"}
        if session.status != "finished":
            logger.warning(
                "finish_session_postprocess_session_not_finished",
                session_id=session_id,
                user_id=user_id,
                status=session.status,
            )
            return {"ok": False, "reason": "session_not_finished"}

        result = await db.execute(
            select(Workout)
            .options(selectinload(Workout.exercises).selectinload(WorkoutExercise.sets))
            .filter(Workout.id == session.workout_id)
        )
        workout = result.scalars().first()
        workout_id: Optional[int] = int(workout.id) if workout and workout.id is not None else None
        applied_plan_id: Optional[int] = (
            int(workout.applied_plan_id) if workout and workout.applied_plan_id is not None else None
        )

        sync_payload = None
        if workout:
            try:
                finished_at = session.finished_at or datetime.now(timezone.utc).replace(tzinfo=None)
                sync_payload = await service._prepare_user_max_payload(workout, session, finished_at)
            except Exception as exc:  # pragma: no cover - best effort logging
                logger.exception(
                    "finish_session_postprocess_user_max_payload_failed",
                    exc_info=exc,
                    session_id=session_id,
                    workout_id=workout_id,
                )

        entries_count = 0
        if sync_payload:
            try:
                await service.user_max_client.push_entries(sync_payload, user_id=user_id)
                entries_count = len(sync_payload)
            except Exception as exc:  # pragma: no cover - best effort logging
                logger.exception(
                    "finish_session_postprocess_push_entries_failed",
                    exc_info=exc,
                    session_id=session_id,
                    workout_id=workout_id,
                )

        suggestion: Optional[Dict[str, Any]] = None
        if applied_plan_id:
            try:
                suggestion = await service._compute_macro_suggestion(applied_plan_id)
                session.macro_suggestion = suggestion
                await db.commit()
                await db.refresh(session)
                try:
                    base_url = os.getenv("PLANS_SERVICE_URL")
                    if not base_url:
                        raise RuntimeError("PLANS_SERVICE_URL is not set")
                    base_url = base_url.rstrip("/")
                    adv_url = f"{base_url}/plans/applied-plans/{applied_plan_id}/advance-index?by=1"
                    headers = {"X-User-Id": user_id}
                    async with httpx.AsyncClient(timeout=4.0) as client:
                        resp = await client.post(adv_url, headers=headers)
                        if resp.status_code >= 400:
                            logger.warning(
                                "finish_session_postprocess_advance_index_non_2xx",
                                applied_plan_id=applied_plan_id,
                                status=resp.status_code,
                            )
                except Exception as exc:  # pragma: no cover - best effort logging
                    logger.exception(
                        "finish_session_postprocess_advance_index_failed",
                        exc_info=exc,
                        session_id=session_id,
                        workout_id=workout_id,
                        applied_plan_id=applied_plan_id,
                    )
            except Exception as exc:  # pragma: no cover - best effort logging
                logger.exception(
                    "finish_session_postprocess_macro_failed",
                    exc_info=exc,
                    session_id=session_id,
                    workout_id=workout_id,
                    applied_plan_id=applied_plan_id,
                )

        social_posted = False
        if workout_id is not None:
            try:
                await service._post_social_workout_completion(workout_id, session)
                social_posted = True
            except Exception as exc:  # pragma: no cover - best effort logging
                logger.exception(
                    "finish_session_postprocess_social_failed",
                    exc_info=exc,
                    session_id=session_id,
                    workout_id=workout_id,
                )

        return {
            "ok": True,
            "session_id": session_id,
            "workout_id": workout_id,
            "applied_plan_id": applied_plan_id,
            "user_max_entries_count": int(entries_count),
            "has_macro_suggestion": bool(suggestion),
            "social_posted": social_posted,
        }


@shared_task(
    bind=True,
    name="workouts.finish_session_postprocess",
    queue=DEFAULT_QUEUE,
    max_retries=2,
)
def finish_session_postprocess_task(self, *, session_id: int, user_id: str) -> Dict[str, Any]:
    try:
        return _run_async(_finish_session_postprocess_async(session_id=session_id, user_id=user_id))
    except Exception as exc:  # pragma: no cover - rely on Celery retry semantics
        logger.exception(
            "finish_session_postprocess_task_failed",
            exc_info=exc,
            session_id=session_id,
            user_id=user_id,
        )
        raise self.retry(exc=exc, countdown=60)
