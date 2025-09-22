from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from typing import List

from ..dependencies import get_session_service
from ..services.session_service import SessionService
from .. import schemas as sm
from ..exceptions import WorkoutNotFoundException, SessionNotFoundException, ActiveSessionNotFoundException

router = APIRouter(prefix="/sessions")


@router.post("/{workout_id}/start", response_model=sm.WorkoutSessionResponse, status_code=status.HTTP_201_CREATED)
async def start_workout_session(
    workout_id: int,
    payload: sm.WorkoutSessionCreate | None = None,
    session_service: SessionService = Depends(get_session_service)
):
    started_at = datetime.now(timezone.utc)
    if payload and payload.started_at:
        started_at = payload.started_at
    session = await session_service.start_workout_session(workout_id, started_at)
    return sm.WorkoutSessionResponse(**session.__dict__)


@router.get("/{workout_id}/active", response_model=sm.WorkoutSessionResponse)
async def get_active_session(
    workout_id: int,
    session_service: SessionService = Depends(get_session_service)
):
    session = await session_service.get_active_session(workout_id)
    if not session:
        raise ActiveSessionNotFoundException(workout_id)
    return sm.WorkoutSessionResponse(**session.__dict__)


@router.get("/{workout_id}/history", response_model=List[sm.WorkoutSessionResponse])
async def get_session_history(
    workout_id: int,
    session_service: SessionService = Depends(get_session_service)
):
    sessions = await session_service.get_session_history(workout_id)
    return [sm.WorkoutSessionResponse(**s.__dict__) for s in sessions]


@router.post("/{session_id}/finish", response_model=sm.WorkoutSessionResponse)
async def finish_session(
    session_id: int,
    session_service: SessionService = Depends(get_session_service)
):
    session = await session_service.finish_session(session_id)
    if not session:
        raise SessionNotFoundException(session_id)
    return sm.WorkoutSessionResponse(**session.__dict__)
