from typing import List, Optional, Dict
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
from datetime import date
from fastapi import FastAPI, Depends, HTTPException, status, APIRouter
from sqlalchemy.orm import Session
import asyncio

from .database import get_db
from .models import UserMax
from . import schemas as schemas  
from .services.true_1rm_service import calculate_true_1rm


app = FastAPI(title="user-max-service", version="0.1.0")
router = APIRouter(prefix="/user-max")


#функция-зависимость для получения UserMax по ID или возврата 404
def get_user_max_or_404(user_max_id: int, db: Session = Depends(get_db)) -> UserMax:
    user_max = db.get(UserMax, user_max_id)
    if user_max is None:
        raise HTTPException(status_code=404, detail=f"UserMax с id {user_max_id} не найден")
    return user_max


@app.get("/health")
async def health():
    logger.info("Healthcheck called")
    return {"status": "ok"}


@router.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@router.post("/", response_model=schemas.UserMaxResponse, status_code=status.HTTP_201_CREATED)
async def create_user_max(user_max: schemas.UserMaxCreate, db: Session = Depends(get_db)):
    db_user_max = UserMax(
        exercise_id=user_max.exercise_id,
        exercise_name=user_max.exercise_name,  # Ensure exercise_name is set
        max_weight=user_max.max_weight,
        rep_max=user_max.rep_max,
        date=user_max.date,
    )
    db.add(db_user_max)
    db.commit()
    db.refresh(db_user_max)
    return db_user_max


@router.get("/", response_model=List[schemas.UserMaxResponse])
async def list_user_maxes(exercise_id: Optional[int] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Получить список записей UserMax с возможностью фильтрации по exercise_id"""
    q = db.query(UserMax)
    if exercise_id is not None:
        q = q.filter(UserMax.exercise_id == exercise_id)
    return q.offset(skip).limit(limit).all()


@router.get("/by_exercise/{exercise_id}", response_model=List[schemas.UserMaxResponse])
async def get_by_exercise(exercise_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Получить записи UserMax для указанного exercise_id с пагинацией"""
    return db.query(UserMax).filter(UserMax.exercise_id == exercise_id).offset(skip).limit(limit).all()


@router.get("/{user_max_id}", response_model=schemas.UserMaxResponse)
async def get_user_max(user_max: UserMax = Depends(get_user_max_or_404)):
    return user_max


@router.put("/{user_max_id}", response_model=schemas.UserMaxResponse)
async def update_user_max(payload: schemas.UserMaxUpdate, user_max: UserMax = Depends(get_user_max_or_404), db: Session = Depends(get_db)):
    allowed_fields = ['exercise_id', 'max_weight', 'rep_max', 'true_1rm', 'verified_1rm']
    for k, v in payload.model_dump().items():
        if k == 'date':
            raise HTTPException(status_code=400, detail="date field is not allowed to update")
        if k in allowed_fields:
            setattr(user_max, k, v)
    db.commit()
    db.refresh(user_max)
    return user_max


@router.delete("/{user_max_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_max(user_max: UserMax = Depends(get_user_max_or_404), db: Session = Depends(get_db)):
    db.delete(user_max)
    db.commit()
    return None


@router.get("/{user_max_id}/calculate-true-1rm", response_model=float)
async def calculate_true_1rm_endpoint(user_max: UserMax = Depends(get_user_max_or_404)):
    return calculate_true_1rm(user_max)


@router.get("/by-exercises", response_model=List[schemas.UserMaxResponse])
async def get_user_maxes_by_exercises(exercise_ids: List[int], db: Session = Depends(get_db)):
    """Получить записи UserMax по списку ID упражнений"""
    if not all(isinstance(id, int) for id in exercise_ids):
        raise HTTPException(400, "Некорректные ID упражнений")
    return db.query(UserMax).filter(UserMax.exercise_id.in_(exercise_ids)).all()


@router.put("/{user_max_id}/verify", response_model=schemas.UserMaxResponse)
async def verify_1rm(verified_1rm: float, user_max: UserMax = Depends(get_user_max_or_404), db: Session = Depends(get_db)):
    user_max.verified_1rm = verified_1rm
    db.commit()
    db.refresh(user_max)
    return user_max


@router.post("/bulk", response_model=List[schemas.UserMaxBulkResponse])
async def create_bulk_user_max(user_maxes: List[schemas.UserMaxCreate], db: Session = Depends(get_db)):
    """Создать несколько записей UserMax за один запрос"""
    logger.info(f"Received bulk create request with {len(user_maxes)} items")
    db_user_maxes = []
    for um in user_maxes:
        logger.info(f"Creating UserMax for exercise: {um.exercise_id}")
        db_um = UserMax(**um.model_dump())
        db.add(db_um)
        db_user_maxes.append(db_um)
    db.commit()
    for um in db_user_maxes:
        db.refresh(um)
    return db_user_maxes

from .schemas import UserMaxCreate, UserMaxResponse, UserMaxUpdate, UserMaxBulkResponse

app.include_router(router)