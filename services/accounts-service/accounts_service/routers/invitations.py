from datetime import datetime, timedelta
import secrets
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..deps import get_db, get_current_uid
from ..models import Invitation, User, CoachClientLink
from ..schemas import InvitationCreate, InvitationOut, InvitationsListOut
from ..services import get_or_create_user, reactivate_or_create_link

router = APIRouter()


def _generate_code() -> str:
    return secrets.token_urlsafe(8)


@router.get("/invitations", response_model=InvitationsListOut)
def list_invitations(db: Session = Depends(get_db), uid: str = Depends(get_current_uid)):
    coach = get_or_create_user(db, uid)
    invs = (
        db.query(Invitation)
        .filter(Invitation.coach_user_id == coach.id)
        .order_by(Invitation.created_at.desc())
        .all()
    )
    items: List[InvitationOut] = [InvitationOut.model_validate(i) for i in invs]
    return InvitationsListOut(items=items)


@router.post("/clients/invite", response_model=InvitationOut, status_code=status.HTTP_201_CREATED)
def create_invitation(payload: InvitationCreate, db: Session = Depends(get_db), uid: str = Depends(get_current_uid)):
    coach = get_or_create_user(db, uid)
    # Basic guardrails
    if payload.email_or_user_id in (coach.id, coach.firebase_uid, coach.email):
        raise HTTPException(status_code=400, detail="Cannot invite yourself")

    # Prevent duplicate active links if user exists
    target_user: User | None = None
    if payload.email_or_user_id:
        target_user = (
            db.query(User)
            .filter(
                (User.id == payload.email_or_user_id)
                | (User.firebase_uid == payload.email_or_user_id)
                | (User.email == payload.email_or_user_id)
            )
            .first()
        )
    if target_user:
        existing_link = (
            db.query(CoachClientLink)
            .filter(
                CoachClientLink.coach_user_id == coach.id,
                CoachClientLink.client_user_id == target_user.id,
                CoachClientLink.status.in_(["active", "pending", "paused"]),
            )
            .first()
        )
        if existing_link:
            raise HTTPException(status_code=409, detail="Client is already linked or pending")

    # Prevent duplicate pending invitations
    dup_inv = (
        db.query(Invitation)
        .filter(
            Invitation.coach_user_id == coach.id,
            Invitation.email_or_user_id == payload.email_or_user_id,
            Invitation.status == "sent",
            (Invitation.expires_at.is_(None)) | (Invitation.expires_at > datetime.utcnow()),
        )
        .first()
    )
    if dup_inv:
        raise HTTPException(status_code=409, detail="An active invitation already exists")
    code = _generate_code()
    expires_at = None
    if payload.ttl_hours and payload.ttl_hours > 0:
        expires_at = datetime.utcnow() + timedelta(hours=payload.ttl_hours)
    inv = Invitation(
        coach_user_id=coach.id,
        email_or_user_id=payload.email_or_user_id,
        code=code,
        status="sent",
        expires_at=expires_at,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return InvitationOut.model_validate(inv)


@router.post("/invitations/{code}/accept", response_model=InvitationOut)
def accept_invitation(code: str, db: Session = Depends(get_db), uid: str = Depends(get_current_uid)):
    client = get_or_create_user(db, uid)
    inv: Invitation | None = db.query(Invitation).filter(Invitation.code == code).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if inv.expires_at and inv.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invitation expired")
    if inv.status not in ("sent", "accepted"):
        raise HTTPException(status_code=400, detail="Invitation is not valid for acceptance")
    # Create or reactivate link
    reactivate_or_create_link(db, coach_user_id=inv.coach_user_id, client_user_id=client.id)

    inv.status = "accepted"
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return InvitationOut.model_validate(inv)
