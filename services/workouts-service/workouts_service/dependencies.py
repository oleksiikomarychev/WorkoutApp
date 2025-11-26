from fastapi import HTTPException, Request
from sentry_sdk import set_tag, set_user


async def get_current_user_id(request: Request) -> str:
    """Extract user_id from X-User-Id header."""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header required")
    set_user({"id": str(user_id)})
    set_tag("service", "workouts-service")
    return user_id
