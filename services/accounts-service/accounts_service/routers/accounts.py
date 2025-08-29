from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import schemas
from ..deps import get_db, get_current_uid
from ..models import User, CoachClientLink
from ..services import get_or_create_user
from ..settings import get_settings

router = APIRouter()


@router.get("/me", response_model=schemas.UserOut)
def me(db: Session = Depends(get_db), uid: str = Depends(get_current_uid)):
    user = get_or_create_user(db, uid)
    return schemas.UserOut.model_validate(user)


@router.patch("/me", response_model=schemas.UserOut)
def update_me(payload: schemas.UserUpdate, db: Session = Depends(get_db), uid: str = Depends(get_current_uid)):
    user = get_or_create_user(db, uid)
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(user, k, v)
    db.add(user)
    db.commit()
    db.refresh(user)
    return schemas.UserOut.model_validate(user)


@router.get("/clients", response_model=schemas.ClientsListOut)
def list_clients(db: Session = Depends(get_db), uid: str = Depends(get_current_uid)):
    # Disable this route when coach-service is enabled (feature-flagged)
    if not get_settings().enable_coach_routers:
        raise HTTPException(status_code=404, detail="Not found")
    coach = get_or_create_user(db, uid)
    # Join links with users to get brief
    q = (
        db.query(CoachClientLink, User)
        .join(User, User.id == CoachClientLink.client_user_id)
        .filter(CoachClientLink.coach_user_id == coach.id)
        .filter(CoachClientLink.status.in_(["active", "pending", "paused"]))
        .order_by(User.display_name.nullslast())
    )
    items: List[schemas.ClientBrief] = []
    for link, cli in q.all():
        items.append(
            schemas.ClientBrief(
                id=cli.id,
                display_name=cli.display_name,
                avatar_url=cli.avatar_url,
                status=link.status,
            )
        )
    return schemas.ClientsListOut(items=items)
