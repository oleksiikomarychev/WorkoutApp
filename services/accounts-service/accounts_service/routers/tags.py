from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..deps import get_db, get_current_uid
from ..models import ClientTag, ClientTagLink
from ..schemas import TagCreate, TagUpdate, TagOut, TagsListOut
from ..services import get_or_create_user, require_client_link, validate_hex_color_or_none

router = APIRouter()


@router.get("/tags", response_model=TagsListOut)
def list_tags(db: Session = Depends(get_db), uid: str = Depends(get_current_uid)):
    coach = get_or_create_user(db, uid)
    tags = db.query(ClientTag).filter(ClientTag.coach_user_id == coach.id).order_by(ClientTag.name.asc()).all()
    return TagsListOut(items=[TagOut.model_validate(t) for t in tags])


@router.post("/tags", response_model=TagOut, status_code=status.HTTP_201_CREATED)
def create_tag(payload: TagCreate, db: Session = Depends(get_db), uid: str = Depends(get_current_uid)):
    coach = get_or_create_user(db, uid)
    validate_hex_color_or_none(payload.color)
    exists = (
        db.query(ClientTag)
        .filter(ClientTag.coach_user_id == coach.id, ClientTag.name == payload.name)
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="Tag with this name already exists")
    tag = ClientTag(coach_user_id=coach.id, name=payload.name, color=payload.color)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return TagOut.model_validate(tag)


@router.patch("/tags/{tag_id}", response_model=TagOut)
def update_tag(tag_id: str, payload: TagUpdate, db: Session = Depends(get_db), uid: str = Depends(get_current_uid)):
    coach = get_or_create_user(db, uid)
    tag = db.query(ClientTag).filter(ClientTag.id == tag_id, ClientTag.coach_user_id == coach.id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    data = payload.model_dump(exclude_unset=True)
    if "color" in data:
        validate_hex_color_or_none(data["color"])
    for k, v in data.items():
        setattr(tag, k, v)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return TagOut.model_validate(tag)


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(tag_id: str, db: Session = Depends(get_db), uid: str = Depends(get_current_uid)):
    coach = get_or_create_user(db, uid)
    tag = db.query(ClientTag).filter(ClientTag.id == tag_id, ClientTag.coach_user_id == coach.id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    # also delete links
    db.query(ClientTagLink).filter(ClientTagLink.tag_id == tag.id, ClientTagLink.coach_user_id == coach.id).delete()
    db.delete(tag)
    db.commit()
    return None


@router.get("/clients/{client_user_id}/tags", response_model=TagsListOut)
def list_client_tags(client_user_id: str, db: Session = Depends(get_db), uid: str = Depends(get_current_uid)):
    coach = get_or_create_user(db, uid)
    # Ensure coach has access to this client
    require_client_link(db, coach_user_id=coach.id, client_user_id=client_user_id)
    # Join tag links with tags
    links = (
        db.query(ClientTag, ClientTagLink)
        .join(ClientTagLink, ClientTagLink.tag_id == ClientTag.id)
        .filter(ClientTagLink.coach_user_id == coach.id, ClientTagLink.client_user_id == client_user_id)
        .all()
    )
    tags: List[TagOut] = [TagOut.model_validate(t) for t, _ in links]
    return TagsListOut(items=tags)


@router.post("/clients/{client_user_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def attach_tag(client_user_id: str, tag_id: str, db: Session = Depends(get_db), uid: str = Depends(get_current_uid)):
    coach = get_or_create_user(db, uid)
    require_client_link(db, coach_user_id=coach.id, client_user_id=client_user_id)
    # ensure tag exists and belongs to coach
    tag = db.query(ClientTag).filter(ClientTag.id == tag_id, ClientTag.coach_user_id == coach.id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    exists = (
        db.query(ClientTagLink)
        .filter(
            ClientTagLink.tag_id == tag_id,
            ClientTagLink.client_user_id == client_user_id,
            ClientTagLink.coach_user_id == coach.id,
        )
        .first()
    )
    if not exists:
        db.add(ClientTagLink(tag_id=tag_id, client_user_id=client_user_id, coach_user_id=coach.id))
        db.commit()
    return None


@router.delete("/clients/{client_user_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def detach_tag(client_user_id: str, tag_id: str, db: Session = Depends(get_db), uid: str = Depends(get_current_uid)):
    coach = get_or_create_user(db, uid)
    require_client_link(db, coach_user_id=coach.id, client_user_id=client_user_id)
    db.query(ClientTagLink).filter(
        ClientTagLink.tag_id == tag_id,
        ClientTagLink.client_user_id == client_user_id,
        ClientTagLink.coach_user_id == coach.id,
    ).delete()
    db.commit()
    return None
