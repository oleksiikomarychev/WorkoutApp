from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import get_db, get_current_uid
from ..models import CoachClientLink
from ..schemas import ClientBrief, ClientsListOut

router = APIRouter()


@router.get("/clients", response_model=ClientsListOut)
def list_clients(db: Session = Depends(get_db), uid: str = Depends(get_current_uid)):
    # List clients for the current coach using local CoachClientLink snapshots
    links: List[CoachClientLink] = (
        db.query(CoachClientLink)
        .filter(
            CoachClientLink.coach_user_id == uid,
            CoachClientLink.status.in_(["active", "pending", "paused"]),
        )
        .order_by(CoachClientLink.client_display_name.is_(None), CoachClientLink.client_display_name.asc())
        .all()
    )
    items: List[ClientBrief] = [
        ClientBrief(
            id=link.client_user_id,
            display_name=link.client_display_name,
            avatar_url=link.client_avatar_url,
            status=link.status,
        )
        for link in links
    ]
    return ClientsListOut(items=items)
