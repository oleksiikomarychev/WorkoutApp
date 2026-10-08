from backend_common.dependencies import make_get_current_user_id, make_get_db_async

from exercises_service.database import AsyncSessionLocal
from exercises_service.services.exercise_service import ExerciseService

get_db = make_get_db_async(AsyncSessionLocal)


def get_exercise_service() -> ExerciseService:
    return ExerciseService()


get_current_user_id = make_get_current_user_id("exercises-service")


def get_dependencies():
    return {
        "get_db": get_db,
        "get_exercise_service": get_exercise_service,
        "get_current_user_id": get_current_user_id,
    }
