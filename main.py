{{ ... }}
from app.routers import workouts, exercises, user_maxes

app = FastAPI()

# Include routers
app.include_router(workouts.router)
app.include_router(exercises.router)
app.include_router(user_maxes.router)

# CORS Middleware
{{ ... }}
