from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app import workout_schemas, workout_models as models
from app.database import get_db

router = APIRouter(redirect_slashes=False)

@router.post("/", response_model=workout_schemas.Exercise)
def create_exercise(exercise: workout_schemas.ExerciseCreate, db: Session = Depends(get_db)):
    workout = db.query(models.Workout).filter(models.Workout.id == exercise.workout_id).first()
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    db_exercise = models.Exercise(**exercise.model_dump())
    db.add(db_exercise)
    db.commit()
    db.refresh(db_exercise)
    return db_exercise

@router.get("/", response_model=List[workout_schemas.Exercise])
def read_exercises(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    exercises = db.query(models.Exercise).offset(skip).limit(limit).all()
    return exercises

@router.get("/list", response_model=List[workout_schemas.ExerciseList])
def read_exercise_list(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    exercises = db.query(models.ExerciseList).offset(skip).limit(limit).all()
    return exercises

@router.post("/list", response_model=workout_schemas.ExerciseList)
def create_exercise_list(exercise: workout_schemas.ExerciseListCreate, db: Session = Depends(get_db)):
    db_exercise = models.ExerciseList(**exercise.model_dump())
    db.add(db_exercise)
    db.commit()
    db.refresh(db_exercise)
    return db_exercise

@router.get("/{exercise_id}", response_model=workout_schemas.Exercise)
def read_exercise(exercise_id: int, db: Session = Depends(get_db)):
    exercise = db.query(models.Exercise).filter(models.Exercise.id == exercise_id).first()
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return exercise

@router.put("/{exercise_id}", response_model=workout_schemas.Exercise)
def update_exercise(exercise_id: int, exercise: workout_schemas.ExerciseCreate, db: Session = Depends(get_db)):
    db_exercise = db.query(models.Exercise).filter(models.Exercise.id == exercise_id).first()
    if db_exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    
    for key, value in exercise.model_dump().items():
        setattr(db_exercise, key, value)
    
    db.commit()
    db.refresh(db_exercise)
    return db_exercise

@router.delete("/{exercise_id}")
def delete_exercise(exercise_id: int, db: Session = Depends(get_db)):
    db_exercise = db.query(models.Exercise).filter(models.Exercise.id == exercise_id).first()
    if db_exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    
    db.delete(db_exercise)
    db.commit()
    return {"detail": "Exercise deleted"}
