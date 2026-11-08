"""Main FastAPI application for Messaging Service."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from channels import router as channels_router
from config import settings
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from idempotency import IdempotencyMiddleware
from messages import router as messages_router
from presence_api import router as presence_router
from redis_publisher import start_publisher, stop_publisher
from webhooks import router as webhooks_router
from websocket_handler import handle_websocket, heartbeat_monitor


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown tasks gracefully."""
    heartbeat_task = asyncio.create_task(heartbeat_monitor())
    publisher_task = asyncio.create_task(start_publisher())
    try:
        yield
    finally:
        heartbeat_task.cancel()
        await stop_publisher()
        publisher_task.cancel()
        await asyncio.gather(heartbeat_task, publisher_task, return_exceptions=True)


# Create FastAPI app
app = FastAPI(
    title="Messaging Service",
    description="Messaging and real-time communication service",
    version="1.0.0",
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
app.include_router(channels_router)
app.include_router(messages_router)
app.include_router(presence_router)
app.include_router(webhooks_router)


# WebSocket endpoint
@app.websocket("/messaging/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time messaging.

    Accepts connections from Gateway with X-User-Id header or user_id query parameter.
    """
    await handle_websocket(websocket)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.service_name,
    }


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "service": settings.service_name,
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
