from exercises_service.database import get_db
from exercises_service.models import ExerciseList
from exercises_service.schemas.exercise import ExerciseExistsResponse
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("/{exercise_id}/exists", response_model=ExerciseExistsResponse)
async def exercise_exists(exercise_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ExerciseList).filter(ExerciseList.id == exercise_id))
    exists = result.scalars().first() is not None
    return ExerciseExistsResponse(exists=exists)
