from fastapi import FastAPI
from .db import init_db
from .settings import get_settings
from .routers import accounts
from .routers import notes, tags, invitations


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")

    # DB init (SQLite fallback creates tables if not exist)
    init_db()

    # Routers
    app.include_router(accounts.router, prefix="/api/v1/accounts", tags=["accounts"])
    if settings.enable_coach_routers:
        app.include_router(notes.router, prefix="/api/v1/accounts", tags=["notes"])
        app.include_router(tags.router, prefix="/api/v1/accounts", tags=["tags"])
        app.include_router(invitations.router, prefix="/api/v1/accounts", tags=["invitations"])

    @app.get("/api/v1/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
