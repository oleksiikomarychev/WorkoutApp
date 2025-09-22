from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .services.workout_service import WorkoutService
from .services.session_service import SessionService


async def get_workout_service(db: AsyncSession = Depends(get_db)) -> WorkoutService:
    return WorkoutService(db)


async def get_session_service(db: AsyncSession = Depends(get_db)) -> SessionService:
    return SessionService(db)
