from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas.workout_generation import WorkoutGenerationRequest, WorkoutGenerationResponse
from ..services.workout_service import WorkoutService
from ..services.rpc_client import PlansServiceRPC  # Import the RPC client

router = APIRouter(prefix="/workout-generation")

@router.post("/generate", response_model=WorkoutGenerationResponse)
async def generate_workouts(request: WorkoutGenerationRequest, db: Session = Depends(get_db)):
    plans_rpc = PlansServiceRPC()  # Create RPC client instance
    service = WorkoutService(db, plans_rpc)  # Pass both required arguments
    try:
        workout_ids = await service.generate_workouts(request)
        return {"workout_ids": workout_ids}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
