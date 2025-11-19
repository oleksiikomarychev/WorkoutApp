from typing import List, Optional, Dict
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
from datetime import date
from fastapi import FastAPI, Depends, HTTPException, status, APIRouter, Query
from sqlalchemy.orm import Session
import asyncio

from .database import get_db
from .models import UserMax
from . import schemas as schemas  
from .services.true_1rm_service import calculate_true_1rm
from .services.exercise_service import get_exercise_name_by_id
from .services.analysis_service import compute_weak_muscles
from .dependencies import get_current_user_id


app = FastAPI(title="user-max-service", version="0.1.0")
router = APIRouter(prefix="/user-max")


def get_user_max_or_404(user_max_id: int, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)) -> UserMax:
    """Get UserMax by ID, ensuring it belongs to the current user."""
    user_max = db.query(UserMax).filter(
        UserMax.id == user_max_id,
        UserMax.user_id == user_id
    ).first()
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
async def create_user_max(user_max: schemas.UserMaxCreate, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    # Fetch exercise name automatically
    try:
        exercise_name = get_exercise_name_by_id(user_max.exercise_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error fetching exercise name: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch exercise name: {str(e)}"
        )
    # Upsert by (user_id, exercise_id, rep_max, date)
    existing = (
        db.query(UserMax)
        .filter(
            UserMax.user_id == user_id,
            UserMax.exercise_id == user_max.exercise_id,
            UserMax.rep_max == user_max.rep_max,
            UserMax.date == user_max.date,
        )
        .first()
    )
    if existing:
        # Keep the best weight for the day and update name if changed
        try:
            if user_max.max_weight is not None and float(user_max.max_weight) > float(existing.max_weight or 0):
                existing.max_weight = user_max.max_weight
        except Exception:
            # If comparison fails for any reason, just keep existing value
            pass
        if exercise_name and existing.exercise_name != exercise_name:
            existing.exercise_name = exercise_name
        # Optional fields
        if user_max.true_1rm is not None:
            existing.true_1rm = user_max.true_1rm
        if user_max.verified_1rm is not None:
            existing.verified_1rm = user_max.verified_1rm
        if user_max.source is not None:
            existing.source = user_max.source
        db.commit()
        db.refresh(existing)
        return existing

    db_user_max = UserMax(
        user_id=user_id,
        exercise_id=user_max.exercise_id,
        exercise_name=exercise_name,
        max_weight=user_max.max_weight,
        rep_max=user_max.rep_max,
        date=user_max.date,
        true_1rm=user_max.true_1rm,
        verified_1rm=user_max.verified_1rm,
        source=user_max.source,
    )
    db.add(db_user_max)
    db.commit()
    db.refresh(db_user_max)
    return db_user_max


@router.get("/", response_model=List[schemas.UserMaxResponse])
async def list_user_maxes(exercise_id: Optional[int] = None, skip: int = 0, limit: int = 100, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Получить список записей UserMax с возможностью фильтрации по exercise_id"""
    q = db.query(UserMax).filter(UserMax.user_id == user_id)
    if exercise_id is not None:
        q = q.filter(UserMax.exercise_id == exercise_id)
    return q.offset(skip).limit(limit).all()


@router.get("/by_exercise/{exercise_id}", response_model=List[schemas.UserMaxResponse])
async def get_by_exercise(exercise_id: int, skip: int = 0, limit: int = 100, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Получить записи UserMax для указанного exercise_id с пагинацией"""
    return db.query(UserMax).filter(
        UserMax.user_id == user_id,
        UserMax.exercise_id == exercise_id
    ).offset(skip).limit(limit).all()


@router.get("/by-exercises", response_model=List[schemas.UserMaxResponse])
async def get_user_maxes_by_exercises(exercise_ids: List[int], user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Получить записи UserMax по списку ID упражнений"""
    if not all(isinstance(id, int) for id in exercise_ids):
        raise HTTPException(400, "Некорректные ID упражнений")
    return db.query(UserMax).filter(
        UserMax.user_id == user_id,
        UserMax.exercise_id.in_(exercise_ids)
    ).all()


@router.get("/by-ids", response_model=List[schemas.UserMaxResponse])
async def get_user_maxes_by_ids(ids: List[int] = Query(..., alias="ids"), user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Получить записи UserMax по списку их идентификаторов"""
    if not ids:
        raise HTTPException(status_code=400, detail="Необходимо указать хотя бы один идентификатор user_max")
    invalid = [value for value in ids if not isinstance(value, int)]
    if invalid:
        raise HTTPException(status_code=400, detail="Список идентификаторов содержит некорректные значения")
    records = db.query(UserMax).filter(
        UserMax.user_id == user_id,
        UserMax.id.in_(ids)
    ).all()
    # Сохраняем порядок, указанный в запросе
    by_id = {um.id: um for um in records}
    ordered = [by_id[id_] for id_ in ids if id_ in by_id]
    return ordered


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


@router.put("/{user_max_id}/verify", response_model=schemas.UserMaxResponse)
async def verify_1rm(verified_1rm: float, user_max: UserMax = Depends(get_user_max_or_404), db: Session = Depends(get_db)):
    user_max.verified_1rm = verified_1rm
    db.commit()
    db.refresh(user_max)
    return user_max


@router.post("/bulk", response_model=List[schemas.UserMaxBulkResponse])
async def create_bulk_user_max(user_maxes: List[schemas.UserMaxCreate], user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Create multiple UserMax records in one request"""
    logger.info(f"Received bulk create request with {len(user_maxes)} items for user {user_id}")
    
    # Collect all exercise IDs
    exercise_ids = [um.exercise_id for um in user_maxes]

    # Fetch all exercise names at once
    exercise_names: Dict[int, str] = {}
    for exercise_id in exercise_ids:
        try:
            exercise_names[exercise_id] = get_exercise_name_by_id(exercise_id)
        except HTTPException as e:
            # If it's a service unavailable error, log and use a placeholder
            if e.status_code == 503:
                logger.error(f"Exercises-service unavailable for ID {exercise_id}: {e.detail}")
                exercise_names[exercise_id] = "Unknown"
            else:
                # For other HTTP errors, re-raise
                raise
        except Exception as e:
            logger.error(f"Unexpected error fetching exercise name for ID {exercise_id}: {str(e)}")
            exercise_names[exercise_id] = "Unknown"

    # 1) Deduplicate incoming payload by (exercise_id, rep_max, date) taking the max weight
    merged: Dict[tuple, schemas.UserMaxCreate] = {}
    for um in user_maxes:
        key = (um.exercise_id, um.rep_max, um.date)
        if key in merged:
            # keep the best weight
            if um.max_weight > merged[key].max_weight:
                merged[key] = um
        else:
            merged[key] = um

    # 2) Upsert each entry
    results: List[UserMax] = []
    for (exercise_id, rep_max, dt), um in merged.items():
        logger.info(
            "Upserting UserMax user_id=%s exercise_id=%s rep_max=%s date=%s", user_id, exercise_id, rep_max, dt
        )
        existing = (
            db.query(UserMax)
            .filter(
                UserMax.user_id == user_id,
                UserMax.exercise_id == exercise_id,
                UserMax.rep_max == rep_max,
                UserMax.date == dt,
            )
            .first()
        )
        if existing:
            try:
                if float(um.max_weight) > float(existing.max_weight or 0):
                    existing.max_weight = um.max_weight
            except Exception:
                pass
            ex_name = exercise_names.get(exercise_id, "Unknown")
            if ex_name and existing.exercise_name != ex_name:
                existing.exercise_name = ex_name
            if um.true_1rm is not None:
                existing.true_1rm = um.true_1rm
            if um.verified_1rm is not None:
                existing.verified_1rm = um.verified_1rm
            if um.source is not None:
                existing.source = um.source
            results.append(existing)
        else:
            db_um = UserMax(
                user_id=user_id,
                exercise_id=exercise_id,
                exercise_name=exercise_names.get(exercise_id, "Unknown"),
                max_weight=um.max_weight,
                rep_max=rep_max,
                date=dt,
                true_1rm=um.true_1rm,
                verified_1rm=um.verified_1rm,
                source=um.source,
            )
            db.add(db_um)
            results.append(db_um)

    db.commit()
    for um in results:
        db.refresh(um)
    return results

app.include_router(router)


# ------------------------------
# Analysis endpoints
# ------------------------------
@app.get("/user-max/analysis/weak-muscles")
def get_weak_muscles(
    recent_days: int = 180,
    min_records: int = 1,
    synergist_weight: float = 0.25,
    use_llm: bool = False,
    fresh: bool = False,
    # Robust relative normalization flags
    relative_by_exercise: bool = True,
    robust: bool = True,
    quantile_mode: str = "p",
    quantile_p: float = 0.25,
    iqr_floor: float = 0.08,
    sigma_floor: float = 0.06,
    k_shrink: float = 12.0,
    z_clip: float = 3.0,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Analyze user_maxes to identify weaker muscles using exercise metadata.
    - recent_days: size of the recency window for trend calc
    - min_records: minimal number of UserMax per exercise to consider
    - synergist_weight: contribution of synergist_muscles (0..1)
    - fresh: bypass cache if True
    """
    try:
        user_maxes = db.query(UserMax).filter(UserMax.user_id == user_id).all()
        profile = compute_weak_muscles(
            user_maxes=user_maxes,
            recent_days=recent_days,
            min_records=min_records,
            synergist_weight=synergist_weight,
            use_llm=use_llm,
            use_cache=not fresh,
            relative_by_exercise=relative_by_exercise,
            robust=robust,
            quantile_mode=quantile_mode,
            quantile_p=quantile_p,
            iqr_floor=iqr_floor,
            sigma_floor=sigma_floor,
            k_shrink=k_shrink,
            z_clip=z_clip,
        )
        return profile
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")