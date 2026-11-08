"""Social Service main FastAPI application."""
import asyncio
from contextlib import asynccontextmanager
import logging
import os
from typing import Any

from config import settings
from database import get_db
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from idempotency import IdempotencyMiddleware
from models import Comment, Follow, IdempotencyKey, Post, Reaction
from posts import router as posts_router
from redis_publisher import start_publisher, stop_publisher
from sqlalchemy import or_
from sqlalchemy.orm import Session
from subscriptions import router as subscriptions_router
from utils import parse_user_id
from webhooks import router as webhooks_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("social-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup and shutdown events."""
    # Ensure all models are registered
    import models  # noqa: F401

    publisher_task = asyncio.create_task(start_publisher())
    logger.info("Started Redis Streams publisher background task")

    try:
        yield
    finally:
        await stop_publisher()
        publisher_task.cancel()
        try:
            await publisher_task
        except asyncio.CancelledError:
            pass
        logger.info("Stopped Redis Streams publisher background task")


# Create FastAPI app
app = FastAPI(
    title="Social Service",
    version="1.0.0",
    description="Social interactions API for posts, comments, reactions, and subscriptions",
    lifespan=lifespan,
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


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Unwrap structured error payloads if present, else preserve standard detail."""
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/health")
async def health_check() -> JSONResponse:
    """Health check endpoint for monitoring and container orchestration."""
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "healthy",
            "service": "social",
        },
    )


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Social Service", "version": "1.0.0"}


@app.post("/internal/users/{user_id}/purge", tags=["Internal"])
async def purge_user_internal(
    user_id: str,
    db: Session = Depends(get_db),
    x_internal_secret: str | None = Header(None, alias="X-Internal-Secret"),
) -> dict[str, Any]:
    """Internal endpoint to purge user social data (called during account deletion)."""
    expected_secret = (settings.internal_gateway_secret or os.getenv("INTERNAL_GATEWAY_SECRET") or "").strip()
    if not expected_secret or x_internal_secret != expected_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    user_uuid = parse_user_id(user_id)

    try:
        # Delete reactions by user
        db.query(Reaction).filter(Reaction.user_id == user_uuid).delete()

        # Delete comments by user
        db.query(Comment).filter(Comment.author_id == user_uuid).delete()

        # Delete follows (both directions)
        db.query(Follow).filter(
            or_(
                Follow.follower_id == user_uuid,
                Follow.followee_id == user_uuid,
            )
        ).delete()

        # Delete posts by user
        db.query(Post).filter(
            or_(
                Post.author_id == user_uuid,
                Post.firebase_uid == user_id,
            )
        ).delete()

        # Delete idempotency keys by user
        db.query(IdempotencyKey).filter(IdempotencyKey.user_id == user_uuid).delete()

        db.commit()
        logger.info("Purged social data for user %s (%s)", user_id, user_uuid)
        return {"status": "ok", "deleted": True, "user_id": user_id}

    except Exception as e:
        db.rollback()
        logger.error("Failed to purge user %s: %s", user_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to purge user social data: {e}",
        )
