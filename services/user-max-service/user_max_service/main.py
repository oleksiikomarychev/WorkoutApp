import logging
from datetime import date

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, status
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.orm import Session

from . import schemas as schemas
from .database import get_db
from .dependencies import get_current_user_id
from .models import UserMax, UserMaxDailyAgg
from .services.analysis_service import aggregate_exercise_strength_from_daily_agg, compute_weak_muscles
from .services.exercise_service import get_exercise_name_by_id
from .services.true_1rm_service import calculate_true_1rm

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="user-max-service", version="0.1.0")

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
router = APIRouter(prefix="/user-max")


def _recompute_daily_agg_for(db: Session, user_id: str, exercise_id: int, dt: date) -> None:
    rows = (
        db.query(UserMax)
        .filter(
            UserMax.user_id == user_id,
            UserMax.exercise_id == exercise_id,
            UserMax.date == dt,
        )
        .all()
    )
    if not rows:
        agg = (
            db.query(UserMaxDailyAgg)
            .filter(
                UserMaxDailyAgg.user_id == user_id,
                UserMaxDailyAgg.exercise_id == exercise_id,
                UserMaxDailyAgg.date == dt,
            )
            .first()
        )
        if agg:
            db.delete(agg)
        return

    sum_true_1rm = 0.0
    cnt = 0
    for um in rows:
        val = um.verified_1rm if getattr(um, "verified_1rm", None) is not None else calculate_true_1rm(um)
        try:
            v = float(val)
        except (TypeError, ValueError):
            continue
        sum_true_1rm += v
        cnt += 1

    if cnt <= 0:
        return

    agg = (
        db.query(UserMaxDailyAgg)
        .filter(
            UserMaxDailyAgg.user_id == user_id,
            UserMaxDailyAgg.exercise_id == exercise_id,
            UserMaxDailyAgg.date == dt,
        )
        .first()
    )
    if not agg:
        agg = UserMaxDailyAgg(
            user_id=user_id,
            exercise_id=exercise_id,
            date=dt,
            sum_true_1rm=sum_true_1rm,
            cnt=cnt,
        )
        db.add(agg)
    else:
        agg.sum_true_1rm = sum_true_1rm
        agg.cnt = cnt


def get_user_max_or_404(
    user_max_id: int, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)
) -> UserMax:
    user_max = db.query(UserMax).filter(UserMax.id == user_max_id, UserMax.user_id == user_id).first()
    if user_max is None:
        raise HTTPException(status_code=404, detail=f"UserMax с id {user_max_id} не найден")
    return user_max


@app.get("/health")
async def health():
    logger.info("Healthcheck called")
    return {"status": "ok"}


@router.post("/", response_model=schemas.UserMaxResponse, status_code=status.HTTP_201_CREATED)
async def create_user_max(
    user_max: schemas.UserMaxCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        exercise_name = get_exercise_name_by_id(user_max.exercise_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error fetching exercise name: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch exercise name: {str(e)}")

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
        try:
            if user_max.max_weight is not None and float(user_max.max_weight) > float(existing.max_weight or 0):
                existing.max_weight = user_max.max_weight
        except Exception:
            pass
        if exercise_name and existing.exercise_name != exercise_name:
            existing.exercise_name = exercise_name

        if user_max.true_1rm is not None:
            existing.true_1rm = user_max.true_1rm
        if user_max.verified_1rm is not None:
            existing.verified_1rm = user_max.verified_1rm
        if user_max.source is not None:
            existing.source = user_max.source
        _recompute_daily_agg_for(db, user_id, existing.exercise_id, existing.date)
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
    _recompute_daily_agg_for(db, user_id, db_user_max.exercise_id, db_user_max.date)
    db.commit()
    db.refresh(db_user_max)
    return db_user_max


@router.get("/", response_model=list[schemas.UserMaxResponse])
async def list_user_maxes(
    exercise_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    q = db.query(UserMax).filter(UserMax.user_id == user_id)
    if exercise_id is not None:
        q = q.filter(UserMax.exercise_id == exercise_id)
    return q.offset(skip).limit(limit).all()


@router.get("/by_exercise/{exercise_id}", response_model=list[schemas.UserMaxResponse])
async def get_by_exercise(
    exercise_id: int,
    skip: int = 0,
    limit: int = 100,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return (
        db.query(UserMax)
        .filter(UserMax.user_id == user_id, UserMax.exercise_id == exercise_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/by-exercises", response_model=list[schemas.UserMaxResponse])
async def get_user_maxes_by_exercises(
    exercise_ids: list[int],
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if not all(isinstance(id, int) for id in exercise_ids):
        raise HTTPException(400, "Некорректные ID упражнений")
    return db.query(UserMax).filter(UserMax.user_id == user_id, UserMax.exercise_id.in_(exercise_ids)).all()


@router.get("/by-ids", response_model=list[schemas.UserMaxResponse])
async def get_user_maxes_by_ids(
    ids: list[int] = Query(..., alias="ids"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if not ids:
        raise HTTPException(status_code=400, detail="Необходимо указать хотя бы один идентификатор user_max")
    invalid = [value for value in ids if not isinstance(value, int)]
    if invalid:
        raise HTTPException(status_code=400, detail="Список идентификаторов содержит некорректные значения")
    records = db.query(UserMax).filter(UserMax.user_id == user_id, UserMax.id.in_(ids)).all()

    by_id = {um.id: um for um in records}
    ordered = [by_id[id_] for id_ in ids if id_ in by_id]
    return ordered


@router.get("/{user_max_id}", response_model=schemas.UserMaxResponse)
async def get_user_max(user_max: UserMax = Depends(get_user_max_or_404)):
    return user_max


@router.put("/{user_max_id}", response_model=schemas.UserMaxResponse)
async def update_user_max(
    payload: schemas.UserMaxUpdate,
    user_max: UserMax = Depends(get_user_max_or_404),
    db: Session = Depends(get_db),
):
    allowed_fields = ["exercise_id", "max_weight", "rep_max", "true_1rm", "verified_1rm"]
    old_exercise_id = user_max.exercise_id
    old_date = user_max.date
    for k, v in payload.model_dump().items():
        if k == "date":
            raise HTTPException(status_code=400, detail="date field is not allowed to update")
        if k in allowed_fields:
            setattr(user_max, k, v)
    _recompute_daily_agg_for(db, user_max.user_id, old_exercise_id, old_date)
    if user_max.exercise_id != old_exercise_id or user_max.date != old_date:
        _recompute_daily_agg_for(db, user_max.user_id, user_max.exercise_id, user_max.date)
    db.commit()
    db.refresh(user_max)
    return user_max


@router.delete("/{user_max_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_max(user_max: UserMax = Depends(get_user_max_or_404), db: Session = Depends(get_db)):
    user_id = user_max.user_id
    exercise_id = user_max.exercise_id
    dt = user_max.date
    db.delete(user_max)
    _recompute_daily_agg_for(db, user_id, exercise_id, dt)
    db.commit()
    return None


@router.get("/{user_max_id}/calculate-true-1rm", response_model=float)
async def calculate_true_1rm_endpoint(user_max: UserMax = Depends(get_user_max_or_404)):
    return calculate_true_1rm(user_max)


@router.put("/{user_max_id}/verify", response_model=schemas.UserMaxResponse)
async def verify_1rm(
    verified_1rm: float,
    user_max: UserMax = Depends(get_user_max_or_404),
    db: Session = Depends(get_db),
):
    user_max.verified_1rm = verified_1rm
    db.commit()
    db.refresh(user_max)
    return user_max


@router.post("/bulk", response_model=list[schemas.UserMaxBulkResponse])
async def create_bulk_user_max(
    user_maxes: list[schemas.UserMaxCreate],
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    logger.info(f"Received bulk create request with {len(user_maxes)} items for user {user_id}")

    exercise_ids = [um.exercise_id for um in user_maxes]

    exercise_names: dict[int, str] = {}
    for exercise_id in exercise_ids:
        try:
            exercise_names[exercise_id] = get_exercise_name_by_id(exercise_id)
        except HTTPException as e:
            if e.status_code == 503:
                logger.error(f"Exercises-service unavailable for ID {exercise_id}: {e.detail}")
                exercise_names[exercise_id] = "Unknown"
            else:
                raise
        except Exception as e:
            logger.error(f"Unexpected error fetching exercise name for ID {exercise_id}: {str(e)}")
            exercise_names[exercise_id] = "Unknown"

    merged: dict[tuple, schemas.UserMaxCreate] = {}
    for um in user_maxes:
        key = (um.exercise_id, um.rep_max, um.date)
        if key in merged:
            if um.max_weight > merged[key].max_weight:
                merged[key] = um
        else:
            merged[key] = um

    results: list[UserMax] = []
    touched_pairs: set[tuple[int, date]] = set()
    for (exercise_id, rep_max, dt), um in merged.items():
        logger.info(
            "Upserting UserMax user_id=%s exercise_id=%s rep_max=%s date=%s",
            user_id,
            exercise_id,
            rep_max,
            dt,
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

        touched_pairs.add((exercise_id, dt))

    for exercise_id, dt in touched_pairs:
        _recompute_daily_agg_for(db, user_id, exercise_id, dt)

    db.commit()
    for um in results:
        db.refresh(um)
    return results


app.include_router(router)


@app.get("/user-max/analysis/weak-muscles")
def get_weak_muscles(
    recent_days: int = 180,
    min_records: int = 1,
    synergist_weight: float = 0.25,
    use_llm: bool = False,
    fresh: bool = False,
    relative_by_exercise: bool = True,
    robust: bool = True,
    quantile_mode: str = "p",
    quantile_p: float = 0.25,
    iqr_floor: float = 0.08,
    sigma_floor: float = 0.06,
    k_shrink: float = 12.0,
    z_clip: float = 3.0,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        user_maxes = db.query(UserMax).filter(UserMax.user_id == user_id).all()
        daily_rows = db.query(UserMaxDailyAgg).filter(UserMaxDailyAgg.user_id == user_id).all()
        precomputed_ex_strength = aggregate_exercise_strength_from_daily_agg(daily_rows) if daily_rows else None
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
            precomputed_ex_strength=precomputed_ex_strength,
        )
        return profile
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
