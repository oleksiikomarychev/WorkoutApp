from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app import workout_schemas, workout_models as models
from app.database import get_db
from typing import List

router = APIRouter()

@router.post("/", response_model=workout_schemas.Workout, status_code=status.HTTP_201_CREATED)
def create_workout(workout: workout_schemas.WorkoutCreate, db: Session = Depends(get_db)):
    db_workout = models.Workout(**workout.model_dump())
    db.add(db_workout)
    db.commit()
    db.refresh(db_workout)
    return db_workout

@router.get("/", response_model=List[workout_schemas.Workout])
def list_workouts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Workout).offset(skip).limit(limit).all()

@router.get("/{workout_id}", response_model=workout_schemas.Workout)
def get_workout(workout_id: int, db: Session = Depends(get_db)):
    workout = db.get(models.Workout, workout_id)
    if workout is None:
        raise HTTPException(status_code=404, detail="Workout not found")
    return workout

@router.put("/{workout_id}", response_model=workout_schemas.Workout)
def update_workout(workout_id: int, workout: workout_schemas.WorkoutCreate, db: Session = Depends(get_db)):
    db_workout = db.get(models.Workout, workout_id)
    if db_workout is None:
        raise HTTPException(status_code=404, detail="Workout not found")
    
    for key, value in workout.model_dump().items():
        setattr(db_workout, key, value)
    
    db.commit()
    db.refresh(db_workout)
    return db_workout

@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(workout_id: int, db: Session = Depends(get_db)):
    db_workout = db.get(models.Workout, workout_id)
    if not db_workout:
        raise HTTPException(status_code=404, detail="Workout not found")  
    db.delete(db_workout)
    db.commit()
    return None
