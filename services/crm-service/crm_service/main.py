import structlog
from backend_common.fastapi_app import create_service_app
from sentry_sdk import set_tag

from .logging_config import configure_logging
from .routers.analytics import router as analytics_router
from .routers.coach_planning import router as coach_router
from .routers.relationships import router as relationships_router

configure_logging()
set_tag("service", "crm-service")
logger = structlog.get_logger(__name__)

app = create_service_app(
    title="crm-service",
    version="0.1.0",
    description="CRM service for coach-athlete relationships and organizations",
    cors_allow_origins=["*"],
    cors_allow_credentials=True,
    cors_allow_methods=["*"],
    cors_allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(relationships_router)
app.include_router(analytics_router)
app.include_router(coach_router)
