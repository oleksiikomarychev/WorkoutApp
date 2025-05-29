from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from app.database import get_db
from app.services.progressions_service import ProgressionsService
from app import workout_models, workout_schemas

router = APIRouter(prefix="/progressions", tags=["progressions"], redirect_slashes=False)

def get_progressions_service(db: Session = Depends(get_db)) -> ProgressionsService:
    """Dependency to get an instance of ProgressionsService."""
    return ProgressionsService(db)

@router.post("", status_code=status.HTTP_201_CREATED, response_model=workout_schemas.Progressions)
def create_progression(
    progression: workout_schemas.ProgressionsCreate, 
    service: ProgressionsService = Depends(get_progressions_service)
) -> Dict[str, Any]:
    return service.create_progression(progression)

@router.get("", response_model=List[workout_schemas.Progressions])
def list_progressions(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    exercise_id: Optional[int] = Query(None, description="Filter by exercise ID"),
    skip: int = 0, 
    limit: int = 100, 
    service: ProgressionsService = Depends(get_progressions_service)
) -> List[Dict[str, Any]]:
    return service.get_progressions(user_id, exercise_id, skip, limit)

@router.get("/{progression_id}", response_model=workout_schemas.Progressions)
def get_progression(
    progression_id: int, 
    service: ProgressionsService = Depends(get_progressions_service)
) -> Dict[str, Any]:
    progression = service.get_progression(progression_id)
    if not progression:
        raise HTTPException(status_code=404, detail="Progression not found")
    return progression

@router.put("/{progression_id}", response_model=workout_schemas.Progressions)
def update_progression(
    progression_id: int, 
    progression: workout_schemas.ProgressionsCreate, 
    service: ProgressionsService = Depends(get_progressions_service)
) -> Dict[str, Any]:
    updated = service.update_progression(progression_id, progression)
    if not updated:
        raise HTTPException(status_code=404, detail="Progression not found")
    return updated

@router.delete("/{progression_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_progression(
    progression_id: int, 
    service: ProgressionsService = Depends(get_progressions_service)
) -> None:
    success = service.delete_progression(progression_id)
    if not success:
        raise HTTPException(status_code=404, detail="Progression not found")

@router.post("/templates", status_code=status.HTTP_201_CREATED, response_model=workout_schemas.ProgressionTemplate)
def create_progression_template(
    template: workout_schemas.ProgressionTemplateCreate, 
    service: ProgressionsService = Depends(get_progressions_service)
) -> Dict[str, Any]:
    return service.create_progression_template(template)

@router.get("/templates", response_model=List[workout_schemas.ProgressionTemplate])
def list_progression_templates(
    skip: int = 0, 
    limit: int = 100, 
    service: ProgressionsService = Depends(get_progressions_service)
) -> List[Dict[str, Any]]:
    return service.get_progression_templates(skip, limit)

@router.get("/templates/{template_id}", response_model=workout_schemas.ProgressionTemplate)
def get_progression_template(
    template_id: int, 
    service: ProgressionsService = Depends(get_progressions_service)
) -> Dict[str, Any]:
    template = service.get_progression_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Progression template not found")
    return template


@router.post("/llm/generate", status_code=status.HTTP_201_CREATED, response_model=workout_schemas.LLMProgressionResponse)
def generate_llm_progression(
    progression: workout_schemas.LLMProgressionCreate,
    service: ProgressionsService = Depends(get_progressions_service)
) -> Dict[str, Any]:
    """
    Generate a new workout progression using AI.
    """
    return service.create_llm_progression(progression)

@router.get("/llm/generations", response_model=List[workout_schemas.LLMProgressionResponse])
def list_llm_progressions(
    skip: int = 0,
    limit: int = 100,
    service: ProgressionsService = Depends(get_progressions_service)
) -> List[Dict[str, Any]]:
    """
    List all AI-generated progressions with pagination.
    """
    return service.get_llm_progressions(skip=skip, limit=limit)

@router.get("/llm/generations/{generation_id}", response_model=workout_schemas.LLMProgressionResponse)
def get_llm_progression(
    generation_id: int,
    service: ProgressionsService = Depends(get_progressions_service)
) -> Dict[str, Any]:
    """
    Get a specific AI-generated progression by ID.
    """
    progression = service.get_llm_progression(generation_id)
    if not progression:
        raise HTTPException(status_code=404, detail="AI progression not found")
    return progression

@router.put("/llm/generations/{generation_id}", response_model=workout_schemas.LLMProgressionResponse)
def update_llm_progression(
    generation_id: int,
    progression: workout_schemas.LLMProgressionCreate,
    service: ProgressionsService = Depends(get_progressions_service)
) -> Dict[str, Any]:
    """
    Update an AI-generated progression.
    """
    updated = service.update_llm_progression(generation_id, progression)
    if not updated:
        raise HTTPException(status_code=404, detail="AI progression not found")
    return updated

@router.delete("/llm/generations/{generation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_llm_progression(
    generation_id: int,
    service: ProgressionsService = Depends(get_progressions_service)
) -> None:
    """
    Delete an AI-generated progression.
    """
    success = service.delete_llm_progression(generation_id)
    if not success:
        raise HTTPException(status_code=404, detail="AI progression not found")
