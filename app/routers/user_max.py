from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app import workout_schemas, workout_models as models
from app.database import get_db

router = APIRouter(prefix="/user-maxes", tags=["user-maxes"], redirect_slashes=False)

@router.post("", response_model=workout_schemas.UserMax, status_code=status.HTTP_201_CREATED)
def create_user_max(user_max: workout_schemas.UserMaxCreate, db: Session = Depends(get_db)):
    # Verify exercise exists
    exercise = db.get(models.ExerciseList, user_max.exercise_id)
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    
    # Check for existing max for this exercise and user
    existing_max = db.query(models.UserMax).filter(
        models.UserMax.exercise_id == user_max.exercise_id,
        models.UserMax.user_id == user_max.user_id
    ).first()
    
    if existing_max:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User max already exists for this exercise"
        )

    db_user_max = models.UserMax(**user_max.model_dump())
    db.add(db_user_max)
    db.commit()
    db.refresh(db_user_max)
    return db_user_max

@router.get("", response_model=List[workout_schemas.UserMax])
def list_user_maxes(
    user_id: Optional[int] = None,
    exercise_id: Optional[int] = None,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    query = db.query(models.UserMax)
    
    if user_id is not None:
        query = query.filter(models.UserMax.user_id == user_id)
    if exercise_id is not None:
        query = query.filter(models.UserMax.exercise_id == exercise_id)
        
    return query.offset(skip).limit(limit).all()

@router.get("/{user_max_id}", response_model=workout_schemas.UserMax)
def get_user_max(user_max_id: int, db: Session = Depends(get_db)):
    user_max = db.query(models.UserMax).filter(models.UserMax.id == user_max_id).first()
    if user_max is None:
        raise HTTPException(status_code=404, detail="UserMax not found")
    return user_max

@router.put("/{user_max_id}", response_model=workout_schemas.UserMax)
def update_user_max(
    user_max_id: int, 
    user_max: workout_schemas.UserMaxCreate, 
    db: Session = Depends(get_db)
):
    db_user_max = db.query(models.UserMax).filter(models.UserMax.id == user_max_id).first()
    if db_user_max is None:
        raise HTTPException(status_code=404, detail="UserMax not found")
    
    for key, value in user_max.model_dump().items():
        setattr(db_user_max, key, value)
    
    db.commit()
    db.refresh(db_user_max)
    return db_user_max

@router.delete("/{user_max_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_max(user_max_id: int, db: Session = Depends(get_db)):
    db_user_max = db.query(models.UserMax).filter(models.UserMax.id == user_max_id).first()
    if db_user_max is None:
        raise HTTPException(status_code=404, detail="UserMax not found")
    
    db.delete(db_user_max)
    db.commit()
    return None
