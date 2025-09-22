from exercises_service.database import AsyncSessionLocal
from exercises_service.services.exercise_service import ExerciseService
from exercises_service.services.set_service import SetService
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


def get_exercise_service() -> ExerciseService:
    return ExerciseService()

def get_set_service() -> SetService:
    return SetService()

def get_dependencies():
    return {
        "get_db": get_db,
        "get_exercise_service": get_exercise_service,
        "get_set_service": get_set_service
    }
