from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from ..models.exercises import ExerciseList
from ..models.user_max import UserMax
from ..schemas.user_max import UserMaxCreate, UserMaxResponse
from ..dependencies import get_db

router = APIRouter()

@router.post("/", response_model=UserMaxResponse, status_code=status.HTTP_201_CREATED)
def create_user_max(user_max: UserMaxCreate, db: Session = Depends(get_db)):
    exercise = db.get(ExerciseList, user_max.exercise_id)
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    
    existing_max = db.query(UserMax).filter(
        UserMax.exercise_id == user_max.exercise_id
    ).first()
    
    if existing_max:
        for key, value in user_max.model_dump().items():
            setattr(existing_max, key, value)
        db.commit()
        db.refresh(existing_max)
        return existing_max

    db_user_max = UserMax(**user_max.model_dump())
    db.add(db_user_max)
    db.commit()
    db.refresh(db_user_max)
    return db_user_max

@router.get("/", response_model=List[UserMaxResponse])
def list_user_maxes(
    exercise_id: Optional[int] = None,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    query = db.query(UserMax)
    
    if exercise_id is not None:
        query = query.filter(UserMax.exercise_id == exercise_id)
        
    return query.offset(skip).limit(limit).all()

@router.get("/by_exercise/{exercise_id}", response_model=List[UserMaxResponse])
def get_user_maxes_for_exercise(exercise_id: int, db: Session = Depends(get_db)):
    user_maxes = db.query(UserMax).filter(UserMax.exercise_id == exercise_id).all()
    # Return empty list if none found to simplify client logic
    return user_maxes

@router.get("/{user_max_id}", response_model=UserMaxResponse)
def get_user_max(user_max_id: int, db: Session = Depends(get_db)):
    user_max = db.query(UserMax).filter(UserMax.id == user_max_id).first()
    if user_max is None:
        raise HTTPException(status_code=404, detail="UserMax not found")
    return user_max

@router.put("/{user_max_id}", response_model=UserMaxResponse)
def update_user_max(
    user_max_id: int, 
    user_max: UserMaxCreate, 
    db: Session = Depends(get_db)
):
    db_user_max = db.query(UserMax).filter(UserMax.id == user_max_id).first()
    if db_user_max is None:
        raise HTTPException(status_code=404, detail="UserMax not found")
    
    for key, value in user_max.model_dump().items():
        setattr(db_user_max, key, value)
    
    db.commit()
    db.refresh(db_user_max)
    return db_user_max

@router.delete("/{user_max_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_max(user_max_id: int, db: Session = Depends(get_db)):
    db_user_max = db.query(UserMax).filter(UserMax.id == user_max_id).first()
    if db_user_max is None:
        raise HTTPException(status_code=404, detail="UserMax not found")
    
    db.delete(db_user_max)
    db.commit()
    return None
