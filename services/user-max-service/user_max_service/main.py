import asyncio
import hashlib
import logging
import os

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query, status
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.orm import Session

from . import schemas as schemas
from .database import get_db
from .dependencies import get_current_user_id
from .models import UserMax
from .services.user_max_service import UserMaxService

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _mask_uid(uid: str) -> str:
    digest = hashlib.sha256((uid or "").encode("utf-8")).hexdigest()[:12]
    return f"uid:{digest}"


try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    logger.info("uvloop installed and activated")
except ImportError:
    logger.warning("uvloop not available, using default event loop")
except Exception as e:
    logger.warning(f"Failed to install uvloop: {e}")


app = FastAPI(title="user-max-service", version="0.1.0")

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
router = APIRouter(prefix="/user-max")


def get_user_max_service(db: Session = Depends(get_db)) -> UserMaxService:
    return UserMaxService(db)


def get_user_max_or_404(
    user_max_id: int, user_id: str = Depends(get_current_user_id), service: UserMaxService = Depends(get_user_max_service)
) -> UserMax:
    return service.get_user_max_or_404(user_max_id, user_id)


@app.get("/health")
async def health():
    logger.info("Healthcheck called")
    return {"status": "ok"}


@app.post("/internal/users/{user_id}/purge")
async def purge_user_internal(
    user_id: str,
    service: UserMaxService = Depends(get_user_max_service),
    x_internal_secret: str | None = Header(None, alias="X-Internal-Secret"),
):
    expected_secret = (os.getenv("INTERNAL_GATEWAY_SECRET") or "").strip()
    if not expected_secret or x_internal_secret != expected_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    return service.purge_user_data(user_id)


@router.post("/", response_model=schemas.UserMaxResponse, status_code=status.HTTP_201_CREATED)
async def create_user_max(
    user_max: schemas.UserMaxCreate,
    user_id: str = Depends(get_current_user_id),
    service: UserMaxService = Depends(get_user_max_service),
):
    return service.create_user_max(user_max, user_id)


@router.get("/", response_model=list[schemas.UserMaxResponse])
async def list_user_maxes(
    exercise_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
    user_id: str = Depends(get_current_user_id),
    service: UserMaxService = Depends(get_user_max_service),
):
    return service.list_user_maxes(user_id, exercise_id, skip, limit)


@router.get("/by_exercise/{exercise_id}", response_model=list[schemas.UserMaxResponse])
async def get_by_exercise(
    exercise_id: int,
    skip: int = 0,
    limit: int = 100,
    user_id: str = Depends(get_current_user_id),
    service: UserMaxService = Depends(get_user_max_service),
):
    return service.get_by_exercise(user_id, exercise_id, skip, limit)


@router.get("/by-exercises", response_model=list[schemas.UserMaxResponse])
async def get_user_maxes_by_exercises(
    exercise_ids: list[int] = Query(..., alias="exercise_ids"),
    user_id: str = Depends(get_current_user_id),
    service: UserMaxService = Depends(get_user_max_service),
):
    return service.get_user_maxes_by_exercises(user_id, exercise_ids)


@router.get("/by-ids", response_model=list[schemas.UserMaxResponse])
async def get_user_maxes_by_ids(
    ids: list[int] = Query(..., alias="ids"),
    user_id: str = Depends(get_current_user_id),
    service: UserMaxService = Depends(get_user_max_service),
):
    return service.get_user_maxes_by_ids(user_id, ids)


@router.get("/{user_max_id}", response_model=schemas.UserMaxResponse)
async def get_user_max(user_max: UserMax = Depends(get_user_max_or_404)):
    return user_max


@router.put("/{user_max_id}", response_model=schemas.UserMaxResponse)
async def update_user_max(
    payload: schemas.UserMaxUpdate,
    user_max: UserMax = Depends(get_user_max_or_404),
    service: UserMaxService = Depends(get_user_max_service),
):
    return service.update_user_max(user_max, payload)


@router.delete("/{user_max_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_max(
    user_max: UserMax = Depends(get_user_max_or_404), 
    service: UserMaxService = Depends(get_user_max_service)
):
    service.delete_user_max(user_max)
    return None


@router.get("/{user_max_id}/calculate-true-1rm", response_model=float)
async def calculate_true_1rm_endpoint(
    user_max: UserMax = Depends(get_user_max_or_404),
    service: UserMaxService = Depends(get_user_max_service)
):
    return service.calculate_true_1rm(user_max)


@router.put("/{user_max_id}/verify", response_model=schemas.UserMaxResponse)
async def verify_1rm(
    verified_1rm: float,
    user_max: UserMax = Depends(get_user_max_or_404),
    service: UserMaxService = Depends(get_user_max_service),
):
    return service.verify_1rm(user_max, verified_1rm)


@router.post("/bulk", response_model=list[schemas.UserMaxBulkResponse])
async def create_bulk_user_max(
    user_maxes: list[schemas.UserMaxCreate],
    user_id: str = Depends(get_current_user_id),
    service: UserMaxService = Depends(get_user_max_service),
):
    logger.info(f"Received bulk create request with {len(user_maxes)} items for user {_mask_uid(user_id)}")
    return service.bulk_create_user_max(user_maxes, user_id)


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
    service: UserMaxService = Depends(get_user_max_service),
):
    return service.get_weak_muscles_analysis(
        user_id=user_id,
        recent_days=recent_days,
        min_records=min_records,
        synergist_weight=synergist_weight,
        use_llm=use_llm,
        fresh=fresh,
        relative_by_exercise=relative_by_exercise,
        robust=robust,
        quantile_mode=quantile_mode,
        quantile_p=quantile_p,
        iqr_floor=iqr_floor,
        sigma_floor=sigma_floor,
        k_shrink=k_shrink,
        z_clip=z_clip,
    )


@app.on_event("shutdown")
async def shutdown_event():
    from .services.exercise_service import cleanup_async_client
    try:
        await cleanup_async_client()
        logger.info("Async client cleaned up successfully")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
