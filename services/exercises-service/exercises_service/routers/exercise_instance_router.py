from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from exercises_service.repositories.exercise_repository import ExerciseRepository
from exercises_service.services.set_service import SetService
from exercises_service.services.exercise_instance_service import ExerciseInstanceService
from exercises_service import schemas
from exercises_service.dependencies import get_db, get_set_service, get_current_user_id

router = APIRouter(prefix="/instances")

@router.get("/{instance_id}", response_model=schemas.ExerciseInstanceResponse)
async def get_exercise_instance(instance_id: int, db: AsyncSession = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    db_instance = await ExerciseRepository.get_exercise_instance(db, instance_id, user_id)
    if not db_instance:
        raise HTTPException(status_code=404, detail="Exercise instance not found")
    return {
        "id": db_instance.id,
        "exercise_list_id": db_instance.exercise_list_id,
        "sets": SetService.normalize_sets_for_frontend(db_instance.sets or []),
        "notes": db_instance.notes,
        "order": db_instance.order,
        "workout_id": db_instance.workout_id,
        "user_max_id": db_instance.user_max_id,
        "user_id": db_instance.user_id,
    }

@router.post("/workouts/{workout_id}/instances", response_model=schemas.ExerciseInstanceResponse, status_code=status.HTTP_201_CREATED)
async def create_exercise_instance(workout_id: int, instance_data: schemas.ExerciseInstanceCreate, db: AsyncSession = Depends(get_db), set_service: SetService = Depends(get_set_service), user_id: str = Depends(get_current_user_id)):
    service = ExerciseInstanceService(db, set_service, user_id)
    try:
        instance = await service.create_instance(workout_id, instance_data)
        # Преобразуем объект SQLAlchemy в Pydantic модель
        return schemas.ExerciseInstanceResponse.model_validate(instance)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{instance_id}", response_model=schemas.ExerciseInstanceResponse)
async def update_exercise_instance(instance_id: int, instance_update: schemas.ExerciseInstanceBase, db: AsyncSession = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    service = ExerciseInstanceService(db, SetService(), user_id)
    return await service.update_instance(instance_id, instance_update)

@router.put("/{instance_id}/sets/{set_id}", response_model=schemas.ExerciseInstanceResponse)
async def update_exercise_set(instance_id: int, set_id: int, payload: schemas.ExerciseSetUpdate, db: AsyncSession = Depends(get_db), set_service: SetService = Depends(get_set_service), user_id: str = Depends(get_current_user_id)):
    service = ExerciseInstanceService(db, set_service, user_id)
    update_data = payload.model_dump(exclude_unset=True)
    return await service.update_set(instance_id, set_id, update_data)

@router.delete("/{instance_id}/sets/{set_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exercise_set(instance_id: int, set_id: int, db: AsyncSession = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    db_instance = await ExerciseRepository.get_exercise_instance(db, instance_id, user_id)
    if not db_instance:
        raise HTTPException(status_code=404, detail="Exercise instance not found")
    if not isinstance(db_instance.sets, list):
        raise HTTPException(status_code=404, detail="No sets to delete")
    new_sets = [s for s in db_instance.sets if not (isinstance(s, dict) and s.get("id") == set_id)]
    if len(new_sets) == len(db_instance.sets):
        raise HTTPException(status_code=404, detail="Set not found")
    await ExerciseRepository.update_exercise_instance(db, db_instance, {"sets": new_sets})

@router.delete("/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exercise_instance(instance_id: int, db: AsyncSession = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    await ExerciseRepository.delete_exercise_instance(db, instance_id, user_id)

@router.post("/batch", response_model=list[schemas.ExerciseInstanceResponse])
async def create_exercise_instances_batch(instances_data: list[schemas.ExerciseInstanceCreate], db: AsyncSession = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    instances_list = []
    for data in instances_data:
        instance_dict = data.model_dump()
        if 'sets' in instance_dict:
            instance_dict['sets'] = SetService.ensure_set_ids(instance_dict['sets'])
        instances_list.append(instance_dict)
    return await ExerciseRepository.create_exercise_instances_batch(db, instances_list, user_id)

@router.post("/migrate-set-ids", status_code=status.HTTP_200_OK)
async def migrate_set_ids(db: AsyncSession = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    return await ExerciseRepository.migrate_set_ids(db)

@router.get("/workouts/{workout_id}/instances", response_model=list[schemas.ExerciseInstanceResponse])
async def get_instances_by_workout(workout_id: int, db: AsyncSession = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    db_instances = await ExerciseRepository.get_instances_by_workout(db, workout_id, user_id)
    if not db_instances:
        return []
    return [{
        "id": i.id,
        "exercise_list_id": i.exercise_list_id,
        "sets": SetService.normalize_sets_for_frontend(i.sets or []),
        "notes": i.notes,
        "order": i.order,
        "workout_id": i.workout_id,
        "user_max_id": i.user_max_id,
        "user_id": i.user_id,
    } for i in db_instances]
