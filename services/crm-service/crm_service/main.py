import uuid

import structlog
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from sentry_sdk import set_tag

from .logging_config import configure_logging
from .routers.analytics import router as analytics_router
from .routers.coach_planning import router as coach_router
from .routers.relationships import router as relationships_router

configure_logging()
set_tag("service", "crm-service")
logger = structlog.get_logger(__name__)

app = FastAPI(
    title="crm-service",
    version="0.1.0",
    description="CRM service for coach-athlete relationships and organizations",
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


app.include_router(relationships_router)
app.include_router(analytics_router)
app.include_router(coach_router)
