from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app import workout_schemas
from app.repositories.workouts_repository import WorkoutsRepository
from app.dependencies import get_db
from sqlalchemy.orm import Session
from app.workout_models import Workout

router = APIRouter()

def get_workouts_repository(db: Session = Depends(get_db)) -> WorkoutsRepository:
    return WorkoutsRepository(db)

@router.post("/", response_model=workout_schemas.WorkoutResponse, status_code=status.HTTP_201_CREATED)
def create_workout(workout: workout_schemas.WorkoutCreate, repo: WorkoutsRepository = Depends(get_workouts_repository)):
    return repo.create_workout(workout)

@router.get("/", response_model=List[workout_schemas.WorkoutResponse])
def list_workouts(skip: int = 0, limit: int = 100, repo: WorkoutsRepository = Depends(get_workouts_repository)):
    return repo.list_workouts(skip, limit)

@router.get("/{workout_id}", response_model=workout_schemas.WorkoutResponse)
def get_workout(workout_id: int, repo: WorkoutsRepository = Depends(get_workouts_repository)):
    workout = repo.get_workout(workout_id)
    if workout is None:
        raise HTTPException(status_code=404, detail="Workout not found")
    return workout

@router.put("/{workout_id}", response_model=workout_schemas.WorkoutResponse)
def update_workout(workout_id: int, workout: workout_schemas.WorkoutResponse, repo: WorkoutsRepository = Depends(get_workouts_repository)):
    try:
        return repo.update_workout(workout_id, workout)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(workout_id: int, repo: WorkoutsRepository = Depends(get_workouts_repository)):
    repo.delete_workout(workout_id)
