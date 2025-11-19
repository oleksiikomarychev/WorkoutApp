from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..dependencies import get_current_user_id
from ..schemas.workout_generation import WorkoutGenerationRequest, WorkoutGenerationResponse
from ..services.workout_service import WorkoutService
from ..services.rpc_client import PlansServiceRPC, RpeServiceRPC  # Import the RPC clients
import logging
import traceback

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workout-generation")

@router.post("/generate", response_model=WorkoutGenerationResponse)
async def generate_workouts(
    request: WorkoutGenerationRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    http_request: Request = None,
):
    logger.info(f"[GENERATE_WORKOUTS] Starting workout generation for user {user_id}, applied_plan_id={request.applied_plan_id}")
    plans_rpc = PlansServiceRPC()  # Create RPC client instance
    rpe_rpc = RpeServiceRPC()
    # Forward Authorization header (if present) so downstream through gateway works
    headers = {}
    if http_request is not None:
        auth = http_request.headers.get('Authorization')
        if auth:
            headers['Authorization'] = auth
    service = WorkoutService(db, plans_rpc, user_id=user_id, rpe_rpc=rpe_rpc, request_headers=headers)
    try:
        workout_ids, created_count, existing_count = await service.generate_workouts(request)
        logger.info(f"[GENERATE_WORKOUTS] Successfully generated {created_count} new workouts; existing_count={existing_count}")
        return {"workout_ids": workout_ids, "created_count": created_count, "existing_count": existing_count}
    except Exception as e:
        logger.error(f"[GENERATE_WORKOUTS] Failed to generate workouts: {e}")
        logger.error(f"[GENERATE_WORKOUTS] Traceback: {traceback.format_exc()}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
