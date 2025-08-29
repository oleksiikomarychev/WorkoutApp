from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..deps import get_db, get_current_uid
from ..models import ClientNote
from ..schemas import ClientNoteCreate, ClientNoteUpdate, ClientNoteOut, ClientNotesListOut
from ..services import fetch_current_user, require_client_link

router = APIRouter()


@router.get("/clients/{client_user_id}/notes", response_model=ClientNotesListOut)
def list_client_notes(client_user_id: str, db: Session = Depends(get_db), uid: str = Depends(get_current_uid)):
    coach = fetch_current_user(uid)
    require_client_link(db, coach_user_id=coach["id"], client_user_id=client_user_id)
    notes = (
        db.query(ClientNote)
        .filter(ClientNote.coach_user_id == coach["id"], ClientNote.client_user_id == client_user_id)
        .order_by(ClientNote.created_at.desc())
        .all()
    )
    return ClientNotesListOut(items=[ClientNoteOut.model_validate(n) for n in notes])


@router.post("/clients/{client_user_id}/notes", response_model=ClientNoteOut, status_code=status.HTTP_201_CREATED)
def create_client_note(client_user_id: str, payload: ClientNoteCreate, db: Session = Depends(get_db), uid: str = Depends(get_current_uid)):
    coach = fetch_current_user(uid)
    require_client_link(db, coach_user_id=coach["id"], client_user_id=client_user_id)
    note = ClientNote(
        coach_user_id=coach["id"],
        client_user_id=client_user_id,
        text=payload.text,
        visibility=payload.visibility or "coach_only",
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return ClientNoteOut.model_validate(note)


@router.patch("/notes/{note_id}", response_model=ClientNoteOut)
def update_note(note_id: str, payload: ClientNoteUpdate, db: Session = Depends(get_db), uid: str = Depends(get_current_uid)):
    coach = fetch_current_user(uid)
    note = db.query(ClientNote).filter(ClientNote.id == note_id, ClientNote.coach_user_id == coach["id"]).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(note, k, v)
    db.add(note)
    db.commit()
    db.refresh(note)
    return ClientNoteOut.model_validate(note)


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: str, db: Session = Depends(get_db), uid: str = Depends(get_current_uid)):
    coach = fetch_current_user(uid)
    note = db.query(ClientNote).filter(ClientNote.id == note_id, ClientNote.coach_user_id == coach["id"]).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(note)
    db.commit()
    return None
