import uuid

import structlog
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from .logging_config import configure_logging
from .routers.avatars import router as avatars_router
from .routers.profile import router as profile_router
from .routers.users import router as users_router

configure_logging()
logger = structlog.get_logger(__name__)

app = FastAPI(
    title="accounts-service",
    version="0.1.0",
    description="User profiles and settings management",
)

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    CorrelationIdMiddleware,
    header_name="X-Request-ID",
    generator=lambda: str(uuid.uuid4()),
    update_request_header=True,
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(profile_router)
app.include_router(avatars_router)
app.include_router(users_router)
