from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time

# Import routers
from app.routers import workouts, exercises, progressions, user_max, user_router
from app.database import engine, Base

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app with Swagger UI enabled by default
app = FastAPI(
    title="Workout Tracking App",
    description="A comprehensive workout tracking application",
    version="1.0.0",
    docs_url="/docs",  # Explicitly set Swagger UI URL
    redoc_url="/redoc"  # Optional: enable ReDoc
)

# CORS middleware (commented out)
origins = [
     "http://localhost",
     "http://localhost:8000",
     "http://localhost:3000",
     "http://10.0.2.2:8000",
     "*"
 ]
app.add_middleware(
     CORSMiddleware,
     allow_origins=origins,
     allow_credentials=True,
     allow_methods=["*"],
     allow_headers=["*"],
 )

# Include routers
app.include_router(workouts.router, prefix="/workouts", tags=["workouts"])
app.include_router(exercises.router, prefix="/exercises", tags=["exercises"])
app.include_router(progressions.router, prefix="/progressions", tags=["progressions"])
app.include_router(user_max.router, prefix="/user-max", tags=["user-max"])
app.include_router(user_router.router, prefix="/users", tags=["users"])

# Performance middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to Workout Tracking App"}
