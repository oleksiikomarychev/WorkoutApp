from fastapi import APIRouter, Depends
from exercises_service.services.exercise_service import ExerciseService
from exercises_service import schemas
from exercises_service.dependencies import get_exercise_service

router = APIRouter(prefix="")

@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

@router.get("/muscles", response_model=list[schemas.MuscleInfo])
async def list_muscles(service: ExerciseService = Depends(get_exercise_service)) -> list[schemas.MuscleInfo]:
    return [
        schemas.MuscleInfo(key=muscle, label=data['label'], group=data['group'])
        for muscle, data in service.MUSCLE_LABELS.items()
    ]
