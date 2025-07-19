from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.services.progressions_service import ProgressionsService


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_progressions_service(db: Session = Depends(get_db)) -> ProgressionsService:
    return ProgressionsService(db)
