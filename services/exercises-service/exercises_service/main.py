from fastapi import FastAPI

from exercises_service.routers import core_router, exercise_definition_router, exercise_instance_router
from exercises_service.services.exercise_service import ExerciseService  

app = FastAPI(title="exercises-service", version="0.1.0")

@app.get("/health")
async def health():
    return {"status": "ok"}

ExerciseService.load_muscle_metadata()

app.include_router(core_router.router, prefix="/exercises")
app.include_router(exercise_definition_router.router, prefix="/exercises")
app.include_router(exercise_instance_router.router, prefix="/exercises")
