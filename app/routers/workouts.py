from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from app import workout_schemas, workout_models as models
from app.dependencies import get_db
from app.services.workouts_service import WorkoutsService

router = APIRouter()

@router.post("/", response_model=workout_schemas.WorkoutResponse, status_code=status.HTTP_201_CREATED)
def create_workout(workout: workout_schemas.WorkoutCreate, db: Session = Depends(get_db)):
    # Create the workout without progression template
    db_workout = models.Workout(name=workout.name)
    db.add(db_workout)
    db.commit()
    db.refresh(db_workout)
    return db_workout

@router.get("/", response_model=List[workout_schemas.WorkoutResponse])
def list_workouts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    workouts = db.query(models.Workout)\
        .options(joinedload(models.Workout.exercise_instances))\
        .offset(skip)\
        .limit(limit)\
        .all()
    return workouts

@router.get("/{workout_id}", response_model=workout_schemas.WorkoutResponse)
def get_workout(workout_id: int, db: Session = Depends(get_db)):
    db_workout = db.query(models.Workout)\
        .options(joinedload(models.Workout.exercise_instances))\
        .filter(models.Workout.id == workout_id)\
        .first()
        
    if db_workout is None:
        raise HTTPException(status_code=404, detail="Workout not found")
        
    return db_workout

@router.put("/{workout_id}", response_model=workout_schemas.WorkoutResponse)
def update_workout(workout_id: int, workout: workout_schemas.WorkoutCreate, db: Session = Depends(get_db)):
    db_workout = db.query(models.Workout).filter(models.Workout.id == workout_id).first()
    if db_workout is None:
        raise HTTPException(status_code=404, detail="Workout not found")
    
    # Update workout name only
    if hasattr(workout, 'name'):
        db_workout.name = workout.name
    
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
