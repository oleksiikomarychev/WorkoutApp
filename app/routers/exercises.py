from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app import workout_schemas, workout_models as models
from app.database import get_db

router = APIRouter(prefix="/exercises", tags=["exercises"], redirect_slashes=False)

# Exercise list management
@router.get("", response_model=List[workout_schemas.ExerciseList])
def list_exercise_definitions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.ExerciseList).offset(skip).limit(limit).all()

@router.post("", response_model=workout_schemas.ExerciseList)
def create_exercise_definition(exercise: workout_schemas.ExerciseListCreate, db: Session = Depends(get_db)):
    db_exercise = models.ExerciseList(**exercise.model_dump())
    db.add(db_exercise)
    db.commit()
    db.refresh(db_exercise)
    return db_exercise

# Workout exercises
@router.post("/workouts/{workout_id}", response_model=workout_schemas.Exercise, status_code=status.HTTP_201_CREATED)
def create_workout_exercise(
    workout_id: int, 
    exercise: workout_schemas.ExerciseCreate, 
    db: Session = Depends(get_db)
):
    # Verify workout exists
    workout = db.get(models.Workout, workout_id)
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    
    # Verify exercise definition exists
    exercise_def = db.get(models.ExerciseList, exercise.exercise_definition_id)
    if not exercise_def:
        raise HTTPException(status_code=404, detail="Exercise definition not found")
    
    db_exercise = models.Exercise(
        **exercise.model_dump(exclude={"workout_id"}),
        workout_id=workout_id
    )
    db.add(db_exercise)
    db.commit()
    db.refresh(db_exercise)
    return db_exercise

@router.get("", response_model=List[workout_schemas.Exercise])
def list_exercises(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Exercise).offset(skip).limit(limit).all()

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
    
    for key, value in exercise.model_dump().items():
        setattr(db_exercise, key, value)
    
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
