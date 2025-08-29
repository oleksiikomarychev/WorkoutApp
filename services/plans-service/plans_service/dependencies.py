from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from .database import SessionLocal
from .services.workout_service import WorkoutService


async def get_user_id(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
) -> str:
    if x_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-User-Id header is required",
        )
    return x_user_id


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_workout_service(db: Session = Depends(get_db)) -> WorkoutService:
    return WorkoutService(db)
