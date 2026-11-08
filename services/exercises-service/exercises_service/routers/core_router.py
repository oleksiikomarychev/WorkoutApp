from __future__ import annotations

from exercises_service import schemas
from exercises_service.dependencies import get_db, get_exercise_service
from exercises_service.redis_client import RedisClient, get_redis_client
from exercises_service.services.exercise_definition_service import ExerciseDefinitionService
from exercises_service.services.exercise_service import ExerciseService
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="")


@router.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@router.get("/muscles", response_model=list[schemas.MuscleInfo])
async def list_muscles(
    service: ExerciseService = Depends(get_exercise_service),
) -> list[schemas.MuscleInfo]:
    """List supported muscle targets and classifications."""
    labels = service.MUSCLE_LABELS or {}
    return [
        schemas.MuscleInfo(key=muscle, label=data.get("label", muscle), group=data.get("group", ""))
        for muscle, data in labels.items()
    ]


@router.get("/{exercise_list_id}", response_model=schemas.ExerciseListResponse, include_in_schema=False)
async def get_exercise_by_id_compat(
    exercise_list_id: int,
    db: AsyncSession = Depends(get_db),
    redis_client: RedisClient = Depends(get_redis_client),
) -> schemas.ExerciseListResponse:
    """Backward-compatible endpoint for GET /exercises/{exercise_id}."""
    service = ExerciseDefinitionService(db, redis_client)
    definition = await service.get_definition(exercise_list_id)
    if not definition:
        raise HTTPException(status_code=404, detail="Exercise definition not found")
    return definition
