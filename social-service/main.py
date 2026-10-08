import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from idempotency import IdempotencyMiddleware
from posts import router as posts_router
from redis_publisher import start_publisher, stop_publisher
from subscriptions import router as subscriptions_router
from webhooks import router as webhooks_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create FastAPI app
app = FastAPI(
    title="Social Service",
    version="1.0.0",
    description="Social interactions API for posts, comments, reactions, and subscriptions"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add idempotency middleware
app.add_middleware(IdempotencyMiddleware)

# Include routers
app.include_router(posts_router)
app.include_router(subscriptions_router)
app.include_router(webhooks_router)

# Background task for Redis publisher
_publisher_task = None


@app.on_event("startup")
async def startup_event():
    """Initialize database and start background tasks on startup."""
    global _publisher_task
    
    # Import models to register them with Base
    import models  # noqa: F401
    
    # Create tables (in production, use Alembic migrations)
    # Base.metadata.create_all(bind=engine)
    
    # Start Redis Streams publisher background task
    _publisher_task = asyncio.create_task(start_publisher())
    logging.info("Started Redis Streams publisher background task")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global _publisher_task
    
    # Stop Redis Streams publisher
    await stop_publisher()
    
    if _publisher_task:
        _publisher_task.cancel()
        try:
            await _publisher_task
        except asyncio.CancelledError:
            pass
    
    logging.info("Stopped Redis Streams publisher background task")


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and container orchestration."""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "social"
        }
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Social Service", "version": "1.0.0"}
