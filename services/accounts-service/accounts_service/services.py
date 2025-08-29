import re
from datetime import datetime
from typing import Iterable
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .models import User, CoachClientLink


HEX_COLOR_RE = re.compile(r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$")


def get_or_create_user(db: Session, firebase_uid: str) -> User:
    user = db.query(User).filter(User.firebase_uid == firebase_uid).first()
    if user:
        return user
    user = User(firebase_uid=firebase_uid)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def require_client_link(
    db: Session,
    coach_user_id: str,
    client_user_id: str,
    allowed_statuses: Iterable[str] = ("active", "pending", "paused"),
) -> CoachClientLink:
    link = (
        db.query(CoachClientLink)
        .filter(
            CoachClientLink.coach_user_id == coach_user_id,
            CoachClientLink.client_user_id == client_user_id,
        )
        .first()
    )
    if not link:
        # 404: клиент не привязан к тренеру
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client link not found")
    if link.status not in set(allowed_statuses):
        # 403: доступ запрещён для данного статуса связи
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Client link is not in an allowed status")
    return link


def reactivate_or_create_link(db: Session, coach_user_id: str, client_user_id: str) -> CoachClientLink:
    link = (
        db.query(CoachClientLink)
        .filter(
            CoachClientLink.coach_user_id == coach_user_id,
            CoachClientLink.client_user_id == client_user_id,
        )
        .first()
    )
    if link:
        if link.status in ("ended",):
            link.status = "active"
            link.started_at = link.started_at or datetime.utcnow()
            db.add(link)
            db.commit()
            db.refresh(link)
        return link
    link = CoachClientLink(coach_user_id=coach_user_id, client_user_id=client_user_id, status="active", started_at=datetime.utcnow())
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def validate_hex_color_or_none(value: str | None) -> None:
    if value is None:
        return
    if not HEX_COLOR_RE.match(value):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid color format. Use hex like #RRGGBB or #RGB")
