from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from exercises_service.services.exercise_definition_service import ExerciseDefinitionService
from exercises_service import schemas
from exercises_service.dependencies import get_db

router = APIRouter(prefix="/definitions")

@router.get("/", response_model=list[schemas.ExerciseListResponse])
async def list_exercise_definitions(ids: str | None = None, db: AsyncSession = Depends(get_db)):
    parsed_ids = [int(id_str) for id_str in ids.split(",")] if ids else None
    service = ExerciseDefinitionService(db)
    return await service.list_definitions(parsed_ids)

@router.get("/{exercise_list_id}", response_model=schemas.ExerciseListResponse)
async def get_exercise_definition(exercise_list_id: int, db: AsyncSession = Depends(get_db)):
    service = ExerciseDefinitionService(db)
    definition = await service.get_definition(exercise_list_id)
    if not definition:
        raise HTTPException(status_code=404, detail="Exercise definition not found")
    return definition

@router.post("/", response_model=schemas.ExerciseListResponse, status_code=status.HTTP_201_CREATED)
async def create_exercise_definition(exercise: schemas.ExerciseListCreate, db: AsyncSession = Depends(get_db)):
    service = ExerciseDefinitionService(db)
    return await service.create_definition(exercise)

@router.put("/{exercise_list_id}", response_model=schemas.ExerciseListResponse)
async def update_exercise_definition(exercise_list_id: int, exercise_update: schemas.ExerciseListCreate, db: AsyncSession = Depends(get_db)):
    service = ExerciseDefinitionService(db)
    definition = await service.get_definition(exercise_list_id)
    if not definition:
        raise HTTPException(status_code=404, detail="Exercise definition not found")
    return await service.update_definition(exercise_list_id, exercise_update)

@router.delete("/{exercise_list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exercise_definition(exercise_list_id: int, db: AsyncSession = Depends(get_db)):
    service = ExerciseDefinitionService(db)
    await service.delete_definition(exercise_list_id)
