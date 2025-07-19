from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from pydantic import BaseModel
from app import workout_schemas, workout_models as models
from app.dependencies import get_db
from sqlalchemy.orm.attributes import flag_modified

router = APIRouter()


@router.get("/list", response_model=List[workout_schemas.ExerciseList])
def list_exercise_definitions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.ExerciseList).offset(skip).limit(limit).all()

@router.get("/instances/{instance_id}", response_model=workout_schemas.ExerciseInstanceResponse)
def get_exercise_instance(instance_id: int, db: Session = Depends(get_db)):
    db_instance = db.query(models.ExerciseInstance).options(
        joinedload(models.ExerciseInstance.exercise_definition),
        joinedload(models.ExerciseInstance.progression_template)
    ).filter(models.ExerciseInstance.id == instance_id).first()
    
    if db_instance is None:
        raise HTTPException(status_code=404, detail="Exercise instance not found")
        
    return db_instance

@router.get("/list/{exercise_list_id}", response_model=workout_schemas.ExerciseList)
def get_exercise_definition(exercise_list_id: int, db: Session = Depends(get_db)):
    db_exercise = db.get(models.ExerciseList, exercise_list_id)
    if db_exercise is None:
        raise HTTPException(status_code=404, detail="Exercise definition not found")
    return db_exercise

@router.post("/list", response_model=workout_schemas.ExerciseList)
def create_exercise_definition(exercise: workout_schemas.ExerciseListCreate, db: Session = Depends(get_db)):
    db_exercise = models.ExerciseList(**exercise.model_dump())
    db.add(db_exercise)
    db.commit()
    db.refresh(db_exercise)
    return db_exercise

@router.post("/workouts/{workout_id}/instances", response_model=workout_schemas.ExerciseInstance, status_code=status.HTTP_201_CREATED)
def create_exercise_instance(workout_id: int, instance_data: workout_schemas.ExerciseInstanceCreate, db: Session = Depends(get_db)):
    workout = db.get(models.Workout, workout_id)
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    exercise_def = db.get(models.ExerciseList, instance_data.exercise_list_id)
    if not exercise_def:
        raise HTTPException(status_code=404, detail="Exercise definition not found")

    if instance_data.progression_template_id:
        progression_template = db.get(models.ProgressionTemplate, instance_data.progression_template_id)
        if not progression_template:
            raise HTTPException(status_code=404, detail="Progression template not found")

    data = instance_data.model_dump()
    data['workout_id'] = workout_id
    data['exercise_id'] = instance_data.exercise_list_id
    
    if 'exercise_id' in data:
        del data['exercise_id']
    
    db_instance = models.ExerciseInstance(**data)
    db.add(db_instance)
    db.commit()
    db.refresh(db_instance)
    return workout_schemas.ExerciseInstance.from_orm(db_instance)

@router.put("/instances/{instance_id}", response_model=workout_schemas.ExerciseInstanceResponse)
def update_exercise_instance(instance_id: int, instance_update: workout_schemas.ExerciseInstanceBase, db: Session = Depends(get_db)):
    db_instance = db.query(models.ExerciseInstance).options(
        joinedload(models.ExerciseInstance.exercise_definition),
        joinedload(models.ExerciseInstance.progression_template)
    ).filter(models.ExerciseInstance.id == instance_id).first()
        
    if db_instance is None:
        raise HTTPException(status_code=404, detail="Exercise instance not found")

    if instance_update.progression_template_id is not None:
        progression_template = db.get(models.ProgressionTemplate, instance_update.progression_template_id)
        if not progression_template:
            raise HTTPException(status_code=404, detail="Progression template not found")

    update_data = instance_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_instance, key, value)

    db.commit()
    db.refresh(db_instance)

    return db_instance

@router.put("/list/{exercise_list_id}", response_model=workout_schemas.ExerciseList)
def update_exercise_definition(exercise_list_id: int, exercise_update: workout_schemas.ExerciseListCreate, db: Session = Depends(get_db)):
    db_exercise = db.get(models.ExerciseList, exercise_list_id)
    if db_exercise is None:
        raise HTTPException(status_code=404, detail="Exercise definition not found")

    update_data = exercise_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_exercise, key, value)

    db.commit()
    db.refresh(db_exercise)
    return db_exercise

@router.delete("/instances/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exercise_instance(instance_id: int, db: Session = Depends(get_db)):
    db_instance = db.get(models.ExerciseInstance, instance_id)
    if not db_instance:
        raise HTTPException(status_code=404, detail="Exercise instance not found")

    db.delete(db_instance)
    db.commit()
    return

@router.delete("/list/{exercise_list_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exercise_definition(exercise_list_id: int, db: Session = Depends(get_db)):
    db_exercise = db.get(models.ExerciseList, exercise_list_id)
    if db_exercise is None:
        raise HTTPException(status_code=404, detail="Exercise definition not found")
    db.delete(db_exercise)
    db.commit()
    return
