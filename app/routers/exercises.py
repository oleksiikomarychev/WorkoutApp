from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app import workout_schemas, workout_models as models
from app.database import get_db

router = APIRouter()

@router.get("/list", response_model=List[workout_schemas.ExerciseList])
def list_exercise_definitions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.ExerciseList).offset(skip).limit(limit).all()

@router.post("/list/create", response_model=workout_schemas.ExerciseList)
def create_exercise_definition(exercise: workout_schemas.ExerciseListCreate, db: Session = Depends(get_db)):
    db_exercise = models.ExerciseList(**exercise.model_dump())
    db.add(db_exercise)
    db.commit()
    db.refresh(db_exercise)
    return db_exercise

@router.post("/workouts/{workout_id}", response_model=workout_schemas.Exercise, status_code=status.HTTP_201_CREATED)
def create_workout_exercise(
    workout_id: int, 
    exercise: workout_schemas.ExerciseCreate, 
    db: Session = Depends(get_db)
):
    workout = db.get(models.Workout, workout_id)
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    
    if exercise.exercise_definition_id is not None:
        exercise_def = db.get(models.ExerciseList, exercise.exercise_definition_id)
        if not exercise_def:
            raise HTTPException(status_code=404, detail="Exercise definition not found")
    
    db_exercise = models.Exercise(
        name=exercise.name,
        volume=exercise.volume,
        weight=exercise.weight if exercise.weight is not None else 0,
        workout_id=workout_id,
        exercise_definition_id=exercise.exercise_definition_id,
        intensity=exercise.intensity if hasattr(exercise, 'intensity') else None,
        effort=exercise.effort if hasattr(exercise, 'effort') else None,
    )
    db.add(db_exercise)
    db.commit()
    db.refresh(db_exercise)
    return db_exercise

@router.get("/workouts/{workout_id}", response_model=List[workout_schemas.Exercise])
def list_workout_exercises(workout_id: int, db: Session = Depends(get_db)):
    return db.query(models.Exercise).filter(models.Exercise.workout_id == workout_id).all()

@router.get("/{exercise_id}", response_model=workout_schemas.Exercise)
def get_exercise(exercise_id: int, db: Session = Depends(get_db)):
    exercise = db.query(models.Exercise).filter(models.Exercise.id == exercise_id).first()
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return exercise

@router.put("/{exercise_id}", response_model=workout_schemas.Exercise)
def update_exercise(
    exercise_id: int, 
    exercise: workout_schemas.ExerciseCreate, 
    db: Session = Depends(get_db)
):
    db_exercise = db.query(models.Exercise).filter(models.Exercise.id == exercise_id).first()
    if db_exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    
    if exercise.name is not None:
        db_exercise.name = exercise.name
    if exercise.volume is not None:
        db_exercise.volume = exercise.volume
    if exercise.weight is not None:
        db_exercise.weight = exercise.weight
    if hasattr(exercise, 'intensity') and exercise.intensity is not None:
        db_exercise.intensity = exercise.intensity
    if hasattr(exercise, 'effort') and exercise.effort is not None:
        db_exercise.effort = exercise.effort
    if exercise.exercise_definition_id is not None:
        db_exercise.exercise_definition_id = exercise.exercise_definition_id
    
    db.commit()
    db.refresh(db_exercise)
    return db_exercise

@router.delete("/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exercise(exercise_id: int, db: Session = Depends(get_db)):
    db_exercise = db.query(models.Exercise).filter(models.Exercise.id == exercise_id).first()
    if db_exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    
    db.delete(db_exercise)
    db.commit()
    return None
