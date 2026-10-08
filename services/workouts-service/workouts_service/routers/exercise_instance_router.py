from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from workouts_service import models
from workouts_service.database import get_db
from workouts_service.dependencies import get_current_user_id
from workouts_service.schemas import workout as workout_schemas
from workouts_service.services.exercise_instance_service import ExerciseInstanceService

router = APIRouter(prefix="/instances")


@router.get("/{instance_id}", response_model=workout_schemas.WorkoutExerciseResponse)
async def get_exercise_instance(
    instance_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    service = ExerciseInstanceService(db, user_id)
    instance = await service.get_instance(instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Exercise instance not found")
    return workout_schemas.WorkoutExerciseResponse.model_validate(instance)


@router.post(
    "/workouts/{workout_id}/instances",
    response_model=workout_schemas.WorkoutExerciseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_exercise_instance(
    workout_id: int,
    instance_data: workout_schemas.WorkoutExerciseInstanceCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    service = ExerciseInstanceService(db, user_id)
    try:
        instance = await service.create_instance(workout_id, instance_data)
        return workout_schemas.WorkoutExerciseResponse.model_validate(instance)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{instance_id}", response_model=workout_schemas.WorkoutExerciseResponse)
async def update_exercise_instance(
    instance_id: int,
    instance_update: workout_schemas.WorkoutExerciseInstanceUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    service = ExerciseInstanceService(db, user_id)
    updated = await service.update_instance(instance_id, instance_update)
    return workout_schemas.WorkoutExerciseResponse.model_validate(updated)


@router.patch("/{instance_id}", response_model=workout_schemas.WorkoutExerciseResponse)
async def patch_exercise_instance(
    instance_id: int,
    instance_update: workout_schemas.WorkoutExerciseInstanceUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    service = ExerciseInstanceService(db, user_id)
    updated = await service.update_instance(instance_id, instance_update)
    return workout_schemas.WorkoutExerciseResponse.model_validate(updated)


@router.put("/{instance_id}/sets/{set_id}", response_model=workout_schemas.WorkoutExerciseResponse)
async def update_exercise_set(
    instance_id: int,
    set_id: int,
    payload: workout_schemas.WorkoutSetUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    service = ExerciseInstanceService(db, user_id)
    update_data = payload.model_dump(exclude_unset=True)
    result = await service.update_set(instance_id, set_id, update_data)
    return workout_schemas.WorkoutExerciseResponse.model_validate(result)


@router.delete("/{instance_id}/sets/{set_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exercise_set(
    instance_id: int,
    set_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    service = ExerciseInstanceService(db, user_id)
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
    service = ExerciseInstanceService(db, user_id)
    await service.delete_instance(instance_id)


@router.post("/batch", response_model=list[workout_schemas.WorkoutExerciseResponse])
async def create_exercise_instances_batch(
    instances_data: list[workout_schemas.WorkoutExerciseInstanceBatchCreate],
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    service = ExerciseInstanceService(db, user_id)
    created: list[dict] = []
    for item in instances_data:
        created_one = await service.create_instance(item.workout_id, item.instance)
        created.append(created_one)
    return [workout_schemas.WorkoutExerciseResponse.model_validate(x) for x in created]


@router.post("/migrate-set-ids", status_code=status.HTTP_200_OK)
async def migrate_set_ids(
    batch_size: int = 1000,
    db: AsyncSession = Depends(get_db), 
    user_id: str = Depends(get_current_user_id)
):
    stmt = (
        select(models.WorkoutSet)
        .join(models.WorkoutExercise, models.WorkoutSet.exercise_id == models.WorkoutExercise.id)
        .where(
            models.WorkoutExercise.user_id == user_id,
            models.WorkoutSet.order_index.is_(None),
        )
        .order_by(models.WorkoutSet.exercise_id.asc(), models.WorkoutSet.id.asc())
        .limit(batch_size)
    )
    res = await db.execute(stmt)
    sets = res.scalars().all()
    if not sets:
        return {"updated": 0}

    per_exercise_counter: dict[int, int] = {}
    updated = 0
    for s in sets:
        ex_id = int(s.exercise_id)
        idx = per_exercise_counter.get(ex_id, 0)
        s.order_index = idx
        per_exercise_counter[ex_id] = idx + 1
        updated += 1

    await db.commit()
    return {"updated": updated}


@router.get("/workouts/{workout_id}/instances", response_model=list[workout_schemas.WorkoutExerciseResponse])
async def get_instances_by_workout(
    workout_id: int, db: AsyncSession = Depends(get_db), user_id: str = Depends(get_current_user_id)
):
    service = ExerciseInstanceService(db, user_id)
    instances = await service.get_instances_by_workout(workout_id)
    return [workout_schemas.WorkoutExerciseResponse.model_validate(instance) for instance in instances]
