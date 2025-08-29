from fastapi import FastAPI
from .database import Base, engine
from .routers import accounts as accounts_router
from .routers import notes as notes_router
from .routers import tags as tags_router
from .routers import invitations as invitations_router


def create_app() -> FastAPI:
    app = FastAPI(title="coach-service", version="0.1.0")

    # Ensure tables exist (for local/dev); in Docker we still run Alembic before start
    Base.metadata.create_all(bind=engine)

    # Routers under the existing accounts prefix to keep API contract
    app.include_router(accounts_router.router, prefix="/api/v1/accounts", tags=["coach-accounts"])
    app.include_router(notes_router.router, prefix="/api/v1/accounts", tags=["coach-notes"])
    app.include_router(tags_router.router, prefix="/api/v1/accounts", tags=["coach-tags"])
    app.include_router(invitations_router.router, prefix="/api/v1/accounts", tags=["coach-invitations"])

    @app.get("/api/v1/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
