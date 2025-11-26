from fastapi import HTTPException, Request, status
from sentry_sdk import set_tag, set_user


def get_current_user_id(request: Request) -> str:
    """Extract user ID from X-User-Id header (case-insensitive)."""
    user_id = request.headers.get("x-user-id")  # Case-insensitive by default
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-User-Id header required")
    set_user({"id": str(user_id)})
    set_tag("service", "user-max-service")
    return user_id
