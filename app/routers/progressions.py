from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app import workout_schemas
from app.database import get_db
from app.services.progressions_service import ProgressionsService

router = APIRouter(redirect_slashes=False)

@router.post("", response_model=workout_schemas.Progressions)
def create_progression(progression: workout_schemas.ProgressionsCreate, db: Session = Depends(get_db)) -> Dict[str, Any]:

    service = ProgressionsService(db)
    return service.create_progression(progression)

@router.get("", response_model=List[workout_schemas.Progressions])
def read_progressions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:

    service = ProgressionsService(db)
    return service.get_progressions(skip, limit)

@router.get("/{progression_id}", response_model=workout_schemas.Progressions)
def read_progression(progression_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:

    service = ProgressionsService(db)
    return service.get_progression(progression_id)

@router.put("/{progression_id}", response_model=workout_schemas.Progressions)
def update_progression(progression_id: int, progression: workout_schemas.ProgressionsCreate, db: Session = Depends(get_db)) -> Dict[str, Any]:

    service = ProgressionsService(db)
    return service.update_progression(progression_id, progression)

@router.delete("/{progression_id}")
def delete_progression(progression_id: int, db: Session = Depends(get_db)) -> Dict[str, str]:

    service = ProgressionsService(db)
    return service.delete_progression(progression_id)

@router.post("/template/", response_model=workout_schemas.ProgressionTemplate)
def create_progression_template(template: workout_schemas.ProgressionTemplateCreate, db: Session = Depends(get_db)):

    service = ProgressionsService(db)
    return service.create_progression_template(template)

@router.get("/template/", response_model=List[workout_schemas.ProgressionTemplate])
def read_progression_templates(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):

    service = ProgressionsService(db)
    return service.get_progression_templates(skip, limit)

@router.get("/template/{template_id}", response_model=workout_schemas.ProgressionTemplate)
def read_progression_template(template_id: int, db: Session = Depends(get_db)):

    service = ProgressionsService(db)
    return service.get_progression_template(template_id)
