from typing import List, Optional, Dict

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import UserMax
from . import schemas as sm

app = FastAPI(title="user-max-service", version="0.1.0")


@app.get("/api/v1/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/user-maxes/", response_model=sm.UserMaxResponse, status_code=status.HTTP_201_CREATED)
def create_or_update_user_max(payload: sm.UserMaxCreate, db: Session = Depends(get_db)):
    existing = db.query(UserMax).filter(UserMax.exercise_id == payload.exercise_id).first()
    if existing:
        for k, v in payload.model_dump().items():
            setattr(existing, k, v)
        db.commit()
        db.refresh(existing)
        return existing

    item = UserMax(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.get("/api/v1/user-maxes/", response_model=List[sm.UserMaxResponse])
def list_user_maxes(exercise_id: Optional[int] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    q = db.query(UserMax)
    if exercise_id is not None:
        q = q.filter(UserMax.exercise_id == exercise_id)
    return q.offset(skip).limit(limit).all()


@app.get("/api/v1/user-maxes/by_exercise/{exercise_id}", response_model=List[sm.UserMaxResponse])
def get_by_exercise(exercise_id: int, db: Session = Depends(get_db)):
    return db.query(UserMax).filter(UserMax.exercise_id == exercise_id).all()


@app.get("/api/v1/user-maxes/{user_max_id}", response_model=sm.UserMaxResponse)
def get_user_max(user_max_id: int, db: Session = Depends(get_db)):
    item = db.query(UserMax).filter(UserMax.id == user_max_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="UserMax not found")
    return item


@app.put("/api/v1/user-maxes/{user_max_id}", response_model=sm.UserMaxResponse)
def update_user_max(user_max_id: int, payload: sm.UserMaxCreate, db: Session = Depends(get_db)):
    item = db.query(UserMax).filter(UserMax.id == user_max_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="UserMax not found")
    for k, v in payload.model_dump().items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@app.delete("/api/v1/user-maxes/{user_max_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_max(user_max_id: int, db: Session = Depends(get_db)):
    item = db.query(UserMax).filter(UserMax.id == user_max_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="UserMax not found")
    db.delete(item)
    db.commit()
    return None
