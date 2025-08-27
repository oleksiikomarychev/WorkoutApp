from typing import List, Dict
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import Workout, WorkoutSession
from . import schemas as sm

app = FastAPI(title="workouts-service", version="0.1.0")


@app.get("/api/v1/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/workouts/", response_model=sm.WorkoutResponse, status_code=status.HTTP_201_CREATED)
def create_workout(payload: sm.WorkoutCreate, db: Session = Depends(get_db)):
    item = Workout(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    # For now, exercise_instances are managed by another service; return empty list placeholder
    return sm.WorkoutResponse(**item.__dict__, exercise_instances=[])


@app.get("/api/v1/workouts/", response_model=List[sm.WorkoutResponse])
def list_workouts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    items = db.query(Workout).offset(skip).limit(limit).all()
    return [sm.WorkoutResponse(**i.__dict__, exercise_instances=[]) for i in items]


@app.get("/api/v1/workouts/{workout_id}", response_model=sm.WorkoutResponse)
def get_workout(workout_id: int, db: Session = Depends(get_db)):
    item = db.query(Workout).filter(Workout.id == workout_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Workout not found")
    return sm.WorkoutResponse(**item.__dict__, exercise_instances=[])


@app.put("/api/v1/workouts/{workout_id}", response_model=sm.WorkoutResponse)
def update_workout(workout_id: int, payload: sm.WorkoutUpdate, db: Session = Depends(get_db)):
    item = db.query(Workout).filter(Workout.id == workout_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Workout not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return sm.WorkoutResponse(**item.__dict__, exercise_instances=[])


@app.delete("/api/v1/workouts/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(workout_id: int, db: Session = Depends(get_db)):
    item = db.query(Workout).filter(Workout.id == workout_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Workout not found")
    db.delete(item)
    db.commit()
    return None


# --- Workout Sessions ---
@app.post("/api/v1/workouts/{workout_id}/start", response_model=sm.WorkoutSessionResponse, status_code=status.HTTP_201_CREATED)
def start_workout_session(workout_id: int, payload: sm.WorkoutSessionCreate | None = None, db: Session = Depends(get_db)):
    workout = db.query(Workout).filter(Workout.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    # If an active session exists, return it instead of creating duplicate
    active = (
        db.query(WorkoutSession)
        .filter(WorkoutSession.workout_id == workout_id, WorkoutSession.status == "active")
        .first()
    )
    if active:
        return sm.WorkoutSessionResponse(**active.__dict__)

    started_at = (payload.started_at if payload and payload.started_at else datetime.now(timezone.utc))
    session = WorkoutSession(workout_id=workout_id, started_at=started_at, status="active")
    db.add(session)
    # reflect in workout meta
    workout.started_at = workout.started_at or started_at
    db.commit()
    db.refresh(session)
    return sm.WorkoutSessionResponse(**session.__dict__)


@app.get("/api/v1/workouts/{workout_id}/active", response_model=sm.WorkoutSessionResponse)
def get_active_session(workout_id: int, db: Session = Depends(get_db)):
    session = (
        db.query(WorkoutSession)
        .filter(WorkoutSession.workout_id == workout_id, WorkoutSession.status == "active")
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="No active session")
    return sm.WorkoutSessionResponse(**session.__dict__)


@app.get("/api/v1/workouts/{workout_id}/history", response_model=List[sm.WorkoutSessionResponse])
def get_session_history(workout_id: int, db: Session = Depends(get_db)):
    sessions = db.query(WorkoutSession).filter(WorkoutSession.workout_id == workout_id).order_by(WorkoutSession.id.desc()).all()
    return [sm.WorkoutSessionResponse(**s.__dict__) for s in sessions]


@app.post("/api/v1/sessions/{session_id}/finish", response_model=sm.WorkoutSessionResponse)
def finish_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(WorkoutSession).filter(WorkoutSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status == "finished":
        return sm.WorkoutSessionResponse(**session.__dict__)
    session.status = "finished"
    session.finished_at = datetime.now(timezone.utc)
    # also mark workout completed_at if not set
    workout = db.query(Workout).filter(Workout.id == session.workout_id).first()
    if workout and not workout.completed_at:
        workout.completed_at = session.finished_at
    db.commit()
    db.refresh(session)
    return sm.WorkoutSessionResponse(**session.__dict__)
