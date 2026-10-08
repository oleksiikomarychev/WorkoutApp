"""Main FastAPI application for Messaging Service."""
import asyncio

from channels import router as channels_router
from config import settings
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from idempotency import IdempotencyMiddleware
from messages import router as messages_router
from presence_api import router as presence_router
from redis_publisher import start_publisher
from webhooks import router as webhooks_router
from websocket_handler import handle_websocket, heartbeat_monitor

# Create FastAPI app
app = FastAPI(
    title="Messaging Service",
    description="Messaging and real-time communication service",
    version="1.0.0"
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
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time messaging.
    
    Accepts connections from Gateway with X-User-Id header or user_id query parameter.
    """
    await handle_websocket(websocket)


# Startup event to start heartbeat monitor and Redis publisher
@app.on_event("startup")
async def startup_event():
    """Start background tasks on application startup."""
    asyncio.create_task(heartbeat_monitor())
    asyncio.create_task(start_publisher())


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.service_name
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.service_name,
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
