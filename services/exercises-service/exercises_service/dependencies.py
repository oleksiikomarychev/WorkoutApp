from fastapi import HTTPException, Request, status
from sentry_sdk import set_tag, set_user
from sqlalchemy.ext.asyncio import AsyncSession

from exercises_service.database import AsyncSessionLocal
from exercises_service.services.exercise_service import ExerciseService
from exercises_service.services.set_service import SetService


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


def get_exercise_service() -> ExerciseService:
    return ExerciseService()


def get_set_service() -> SetService:
    return SetService()


def get_current_user_id(request: Request) -> str:
    """Extract user ID from X-User-Id header (case-insensitive)."""
    user_id = request.headers.get("x-user-id")  # Case-insensitive by default
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-User-Id header required")
    set_user({"id": str(user_id)})
    set_tag("service", "exercises-service")
    return user_id


def get_dependencies():
    return {
        "get_db": get_db,
        "get_exercise_service": get_exercise_service,
        "get_set_service": get_set_service,
        "get_current_user_id": get_current_user_id,
    }
