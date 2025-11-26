from exercises_service import schemas
from exercises_service.dependencies import get_current_user_id, get_db, get_set_service
from exercises_service.metrics import (
    EXERCISE_INSTANCES_BATCH_CREATED_TOTAL,
    EXERCISE_INSTANCES_CREATED_TOTAL,
    EXERCISE_SETS_UPDATED_TOTAL,
)
from exercises_service.repositories.exercise_repository import ExerciseRepository
from exercises_service.services.exercise_instance_service import ExerciseInstanceService
from exercises_service.services.set_service import SetService
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/instances")


@router.get("/{instance_id}", response_model=schemas.ExerciseInstanceResponse)
async def get_exercise_instance(
    instance_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    service = ExerciseInstanceService(db, SetService(), user_id)
    instance = await service.get_instance(instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Exercise instance not found")
    return instance


@router.post(
    "/workouts/{workout_id}/instances",
    response_model=schemas.ExerciseInstanceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_exercise_instance(
    workout_id: int,
    instance_data: schemas.ExerciseInstanceCreate,
    db: AsyncSession = Depends(get_db),
    set_service: SetService = Depends(get_set_service),
    user_id: str = Depends(get_current_user_id),
):
    service = ExerciseInstanceService(db, set_service, user_id)
    try:
        instance = await service.create_instance(workout_id, instance_data)
        EXERCISE_INSTANCES_CREATED_TOTAL.inc()
        return schemas.ExerciseInstanceResponse.model_validate(instance)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{instance_id}", response_model=schemas.ExerciseInstanceResponse)
async def update_exercise_instance(
    instance_id: int,
    instance_update: schemas.ExerciseInstanceBase,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    service = ExerciseInstanceService(db, SetService(), user_id)
    updated = await service.update_instance(instance_id, instance_update)
    return schemas.ExerciseInstanceResponse.model_validate(updated)


@router.put("/{instance_id}/sets/{set_id}", response_model=schemas.ExerciseInstanceResponse)
async def update_exercise_set(
    instance_id: int,
    set_id: int,
    payload: schemas.ExerciseSetUpdate,
    db: AsyncSession = Depends(get_db),
    set_service: SetService = Depends(get_set_service),
    user_id: str = Depends(get_current_user_id),
):
    service = ExerciseInstanceService(db, set_service, user_id)
    update_data = payload.model_dump(exclude_unset=True)
    result = await service.update_set(instance_id, set_id, update_data)
    EXERCISE_SETS_UPDATED_TOTAL.inc()
    return schemas.ExerciseInstanceResponse.model_validate(result)


@router.delete("/{instance_id}/sets/{set_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exercise_set(
    instance_id: int,
    set_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    service = ExerciseInstanceService(db, SetService(), user_id)
    try:
        await service.delete_set(instance_id, set_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exercise_instance(
    instance_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    service = ExerciseInstanceService(db, SetService(), user_id)
    await service.delete_instance(instance_id)


@router.post("/batch", response_model=list[schemas.ExerciseInstanceResponse])
async def create_exercise_instances_batch(
    instances_data: list[schemas.ExerciseInstanceCreate],
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    instances_list = []
    for data in instances_data:
        instance_dict = data.model_dump()
        if "sets" in instance_dict:
            instance_dict["sets"] = SetService.ensure_set_ids(instance_dict["sets"])
        instances_list.append(instance_dict)
    result = await ExerciseRepository.create_exercise_instances_batch(db, instances_list, user_id)
    EXERCISE_INSTANCES_BATCH_CREATED_TOTAL.inc(len(result))
    return result


@router.post("/migrate-set-ids", status_code=status.HTTP_200_OK)
async def migrate_set_ids(db: AsyncSession = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    return await ExerciseRepository.migrate_set_ids(db)


@router.get("/workouts/{workout_id}/instances", response_model=list[schemas.ExerciseInstanceResponse])
async def get_instances_by_workout(
    workout_id: int, db: AsyncSession = Depends(get_db), user_id: str = Depends(get_current_user_id)
):
    service = ExerciseInstanceService(db, SetService(), user_id)
    instances = await service.get_instances_by_workout(workout_id)
    return [schemas.ExerciseInstanceResponse.model_validate(instance) for instance in instances]
