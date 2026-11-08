"""Internal user purge router for agent-service."""

from __future__ import annotations

import hmac
import os

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from ..config import settings
from ..dependencies import get_db
from ..models import Avatar, GeneratedPlan

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/internal/users", tags=["internal"])


@router.post("/{user_id}/purge")
def purge_user(
    user_id: str,
    db: Session = Depends(get_db),
    x_internal_secret: str | None = Header(None, alias="X-Internal-Secret"),
) -> dict[str, str | int]:
    expected_secret = (settings.INTERNAL_GATEWAY_SECRET or os.getenv("INTERNAL_GATEWAY_SECRET") or "").strip()
    if not expected_secret or not x_internal_secret or not hmac.compare_digest(x_internal_secret, expected_secret):
        logger.warning("unauthorized_internal_purge_attempt", user_id=user_id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    try:
        deleted_plans = db.query(GeneratedPlan).filter(GeneratedPlan.user_id == user_id).delete(synchronize_session=False)
        deleted_avatars = db.query(Avatar).filter(Avatar.user_id == user_id).delete(synchronize_session=False)
        db.commit()
        logger.info(
            "user_purged_successfully",
            user_id=user_id,
            deleted_plans=deleted_plans,
            deleted_avatars=deleted_avatars,
        )
        return {
            "status": "ok",
            "deleted_plans": deleted_plans,
            "deleted_avatars": deleted_avatars,
        }
    except Exception as exc:
        db.rollback()
        logger.error("failed_to_purge_user", user_id=user_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to purge user data: {exc}",
        )
