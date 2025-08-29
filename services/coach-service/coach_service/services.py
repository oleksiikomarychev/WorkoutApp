import os
import re
from datetime import datetime
from typing import Iterable, Optional, Dict, Any

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .models import CoachClientLink

HEX_COLOR_RE = re.compile(r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$")
ACCOUNTS_SERVICE_URL = os.getenv("ACCOUNTS_SERVICE_URL", "http://accounts-service:8006")


def fetch_current_user(uid: str) -> Dict[str, Any]:
    """
    Ask accounts-service to resolve/create the current user and return its profile.
    This relies on accounts-service accepting X-User-Id header for auth.
    """
    url = f"{ACCOUNTS_SERVICE_URL}/api/v1/accounts/me"
    headers = {"X-User-Id": uid}
    try:
        r = httpx.get(url, headers=headers, timeout=5.0)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Accounts service unavailable: {e}")
    if r.status_code >= 400:
        try:
            detail = r.json()
        except Exception:
            detail = r.text
        raise HTTPException(status_code=502, detail={"message": "Accounts service error", "upstream": detail})
    return r.json()


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client link not found")
    if link.status not in set(allowed_statuses):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Client link is not in an allowed status")
    return link


def reactivate_or_create_link(
    db: Session,
    coach_user_id: str,
    client_user_id: str,
    client_display_name: Optional[str] = None,
    client_avatar_url: Optional[str] = None,
) -> CoachClientLink:
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
        # Update snapshot fields if provided
        if client_display_name is not None:
            link.client_display_name = client_display_name
        if client_avatar_url is not None:
            link.client_avatar_url = client_avatar_url
        db.add(link)
        db.commit()
        db.refresh(link)
        return link
    link = CoachClientLink(
        coach_user_id=coach_user_id,
        client_user_id=client_user_id,
        status="active",
        started_at=datetime.utcnow(),
        client_display_name=client_display_name,
        client_avatar_url=client_avatar_url,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def validate_hex_color_or_none(value: str | None) -> None:
    if value is None:
        return
    if not HEX_COLOR_RE.match(value):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid color format. Use hex like #RRGGBB or #RGB",
        )
