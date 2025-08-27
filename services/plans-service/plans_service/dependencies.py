from fastapi import Depends
from sqlalchemy.orm import Session

from .database import SessionLocal
from .services.workout_service import WorkoutService

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_workout_service(db: Session = Depends(get_db)) -> WorkoutService:
    return WorkoutService(db)
