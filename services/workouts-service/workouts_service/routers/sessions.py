import os
from datetime import datetime, timezone
from typing import List

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from .. import schemas as sm
from ..database import get_db
from ..dependencies import get_current_user_id
from ..exceptions import (
    ActiveSessionNotFoundException,
    SessionNotFoundException,
)
from ..services.session_service import SessionService
from ..tasks.session_tasks import finish_session_postprocess_task

router = APIRouter(prefix="/sessions")

logger = structlog.get_logger(__name__)


def get_session_service(
    db: AsyncSession = Depends(get_db), user_id: str = Depends(get_current_user_id)
) -> SessionService:
    return SessionService(db, user_id=user_id)


@router.get("/history/all", response_model=List[sm.WorkoutSessionResponse])
async def get_all_sessions(
    session_service: SessionService = Depends(get_session_service),
    user_id: str | None = Query(None, description="Override user id (internal use only)"),
    x_internal_secret: str | None = Header(None, alias="X-Internal-Secret"),
):
    target_service = session_service
    if user_id:
        expected_secret = (os.getenv("INTERNAL_GATEWAY_SECRET") or "").strip()
        if not expected_secret or x_internal_secret != expected_secret:
            raise HTTPException(status_code=403, detail="Forbidden")
        override_service = SessionService(session_service.db, user_id=user_id)
        target_service = override_service
    sessions = await target_service.get_all_sessions()
    return [sm.WorkoutSessionResponse(**s.__dict__) for s in sessions]


@router.post(
    "/{workout_id}/start",
    response_model=sm.WorkoutSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_workout_session(
    workout_id: int,
    payload: sm.WorkoutSessionCreate | None = None,
    session_service: SessionService = Depends(get_session_service),
    user_id: str = Depends(get_current_user_id),
):
    started_at = datetime.now(timezone.utc)
    if payload and payload.started_at:
        started_at = payload.started_at
    logger.info(
        "workout_session_start_requested",
        user_id=user_id,
        workout_id=workout_id,
        started_at=started_at.isoformat(),
    )
    session = await session_service.start_workout_session(workout_id, started_at)
    logger.info(
        "workout_session_start_success",
        user_id=user_id,
        workout_id=workout_id,
        session_id=getattr(session, "id", None),
    )
    return sm.WorkoutSessionResponse(**session.__dict__)


@router.get("/{workout_id}/active", response_model=sm.WorkoutSessionResponse)
async def get_active_session(workout_id: int, session_service: SessionService = Depends(get_session_service)):
    session = await session_service.get_active_session(workout_id)
    if not session:
        raise ActiveSessionNotFoundException(workout_id)
    return sm.WorkoutSessionResponse(**session.__dict__)


@router.get("/{workout_id}/history", response_model=List[sm.WorkoutSessionResponse])
async def get_session_history(workout_id: int, session_service: SessionService = Depends(get_session_service)):
    sessions = await session_service.get_session_history(workout_id)
    return [sm.WorkoutSessionResponse(**s.__dict__) for s in sessions]


@router.post("/{session_id}/finish", response_model=sm.WorkoutSessionResponse)
async def finish_session(
    session_id: int,
    session_service: SessionService = Depends(get_session_service),
    user_id: str = Depends(get_current_user_id),
):
    logger.info(
        "workout_session_finish_requested",
        user_id=user_id,
        session_id=session_id,
    )
    session = await session_service.finish_session(session_id)
    if not session:
        raise SessionNotFoundException(session_id)
    logger.info(
        "workout_session_finish_success",
        user_id=user_id,
        session_id=session_id,
        workout_id=getattr(session, "workout_id", None),
    )
    try:
        finish_session_postprocess_task.delay(session_id=session.id, user_id=user_id)
    except Exception:
        logger.exception(
            "workout_session_finish_postprocess_enqueue_failed",
            user_id=user_id,
            session_id=session_id,
        )
    return sm.WorkoutSessionResponse(**session.__dict__)


@router.put("/{session_id}/progress", response_model=sm.WorkoutSessionResponse)
async def update_session_progress(
    session_id: int,
    payload: sm.SessionProgressUpdate,
    session_service: SessionService = Depends(get_session_service),
    user_id: str = Depends(get_current_user_id),
):
    logger.info(
        "workout_session_progress_update",
        user_id=user_id,
        session_id=session_id,
        instance_id=payload.instance_id,
        set_id=payload.set_id,
        completed=payload.completed,
    )
    session = await session_service.update_progress(
        session_id=session_id,
        instance_id=payload.instance_id,
        set_id=payload.set_id,
        completed=payload.completed,
    )
    return sm.WorkoutSessionResponse(**session.__dict__)
