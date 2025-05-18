from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app import workout_schemas, workout_models as models
from app.database import get_db

router = APIRouter(redirect_slashes=False)

@router.post("", response_model=workout_schemas.UserMax)
def create_user_max(user_max: workout_schemas.UserMaxCreate, db: Session = Depends(get_db)):
    exercise = db.query(models.ExerciseList).filter(models.ExerciseList.id == user_max.exercise_id).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    db_user_max = models.UserMax(**user_max.model_dump())
    db.add(db_user_max)
    db.commit()
    db.refresh(db_user_max)
    return db_user_max

@router.get("", response_model=List[workout_schemas.UserMax])
def read_user_maxes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    user_maxes = db.query(models.UserMax).offset(skip).limit(limit).all()
    return user_maxes

@router.get("/{user_max_id}", response_model=workout_schemas.UserMax)
def read_user_max(user_max_id: int, db: Session = Depends(get_db)):
    user_max = db.query(models.UserMax).filter(models.UserMax.id == user_max_id).first()
    if user_max is None:
        raise HTTPException(status_code=404, detail="UserMax not found")
    return user_max

@router.put("/{user_max_id}", response_model=workout_schemas.UserMax)
def update_user_max(user_max_id: int, user_max: workout_schemas.UserMaxCreate, db: Session = Depends(get_db)):
    db_user_max = db.query(models.UserMax).filter(models.UserMax.id == user_max_id).first()
    if db_user_max is None:
        raise HTTPException(status_code=404, detail="UserMax not found")
    
    for key, value in user_max.model_dump().items():
        setattr(db_user_max, key, value)
    
    db.commit()
    db.refresh(db_user_max)
    return db_user_max

@router.delete("/{user_max_id}")
def delete_user_max(user_max_id: int, db: Session = Depends(get_db)):
    db_user_max = db.query(models.UserMax).filter(models.UserMax.id == user_max_id).first()
    if db_user_max is None:
        raise HTTPException(status_code=404, detail="UserMax not found")
    
    db.delete(db_user_max)
    db.commit()
    return {"detail": "UserMax deleted successfully"}
