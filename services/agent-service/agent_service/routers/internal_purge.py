import os

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from ..dependencies import get_db
from ..models import Avatar, GeneratedPlan

router = APIRouter(prefix="/internal/users", tags=["internal"])


@router.post("/{user_id}/purge")
def purge_user(
    user_id: str,
    db: Session = Depends(get_db),
    x_internal_secret: str | None = Header(None, alias="X-Internal-Secret"),
) -> dict[str, str]:
    expected_secret = (os.getenv("INTERNAL_GATEWAY_SECRET") or "").strip()
    if not expected_secret or x_internal_secret != expected_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    db.query(GeneratedPlan).filter(GeneratedPlan.user_id == user_id).delete(synchronize_session=False)
    db.query(Avatar).filter(Avatar.user_id == user_id).delete(synchronize_session=False)
    db.commit()
    return {"status": "ok"}
