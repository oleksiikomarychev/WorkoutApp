from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers.profile import router as profile_router
from .routers.avatars import router as avatars_router

app = FastAPI(
    title="accounts-service",
    version="0.1.0",
    description="User profile and settings management",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(profile_router)
app.include_router(avatars_router)
