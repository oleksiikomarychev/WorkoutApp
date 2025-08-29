from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..dependencies import get_db
from ..services.workout_session_service import WorkoutSessionService
from ..schemas.workout_session import (
    WorkoutSessionResponse,
    SessionProgressUpdate,
    SessionFinishRequest,
)

router = APIRouter()


def get_session_service(db: Session = Depends(get_db)) -> WorkoutSessionService:
    return WorkoutSessionService(db)


@router.post(
    "/workouts/{workout_id}/start",
    response_model=WorkoutSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_session(
    workout_id: int, service: WorkoutSessionService = Depends(get_session_service)
):
    try:
        session = service.start_session(workout_id)
        # If an active session already existed, 200 would be more accurate, but we keep 201 for simplicity
        return session
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/workouts/{workout_id}/active",
    response_model=WorkoutSessionResponse,
)
def get_active_session(
    workout_id: int, service: WorkoutSessionService = Depends(get_session_service)
):
    session = service.get_active_session(workout_id)
    if not session:
        raise HTTPException(status_code=404, detail="No active session")
    return session


@router.get(
    "/workouts/{workout_id}/history",
    response_model=list[WorkoutSessionResponse],
)
def list_sessions(
    workout_id: int, service: WorkoutSessionService = Depends(get_session_service)
):
    return service.list_sessions(workout_id)


@router.put(
    "/sessions/{session_id}/instances/{instance_id}/sets/{set_id}",
    response_model=WorkoutSessionResponse,
)
def update_set_completion(
    session_id: int,
    instance_id: int,
    set_id: int,
    payload: SessionProgressUpdate,
    service: WorkoutSessionService = Depends(get_session_service),
):
    # accept body for flexibility, but path takes precedence
    completed = True if payload.completed is None else payload.completed
    try:
        return service.update_progress(session_id, instance_id, set_id, completed)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/sessions/{session_id}/finish",
    response_model=WorkoutSessionResponse,
)
def finish_session(
    session_id: int,
    payload: SessionFinishRequest,
    service: WorkoutSessionService = Depends(get_session_service),
):
    try:
        return service.finish_session(
            session_id,
            cancelled=payload.cancelled,
            mark_workout_completed=payload.mark_workout_completed,
            device_source=payload.device_source,
            hr_avg=payload.hr_avg,
            hr_max=payload.hr_max,
            hydration_liters=payload.hydration_liters,
            mood=payload.mood,
            injury_flags=payload.injury_flags,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
