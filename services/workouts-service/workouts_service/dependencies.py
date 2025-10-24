from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db


async def get_current_user_id(request: Request) -> str:
    """Extract user_id from X-User-Id header."""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header required")
    return user_id
