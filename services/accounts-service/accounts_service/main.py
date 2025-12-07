import structlog
from backend_common.fastapi_app import create_service_app

from .logging_config import configure_logging
from .routers.avatars import router as avatars_router
from .routers.profile import router as profile_router
from .routers.users import router as users_router

configure_logging()
logger = structlog.get_logger(__name__)

app = create_service_app(
    title="accounts-service",
    version="0.1.0",
    description="User profiles and settings management",
    cors_allow_origins=["*"],
    cors_allow_credentials=True,
    cors_allow_methods=["*"],
    cors_allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(profile_router)
app.include_router(avatars_router)
app.include_router(users_router)
