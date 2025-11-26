from fastapi import HTTPException, Request, status
from sentry_sdk import set_tag, set_user
from sqlalchemy.ext.asyncio import AsyncSession

from .database import AsyncSessionLocal


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


def get_current_user_id(request: Request) -> str:
    user_id = request.headers.get("x-user-id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-User-Id header required")
    set_user({"id": str(user_id)})
    set_tag("service", "crm-service")
    return user_id
