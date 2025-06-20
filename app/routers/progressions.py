from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.workout_schemas import (
    ProgressionTemplateCreate,
    ProgressionTemplateUpdate,
    ProgressionTemplateResponse
)
from app.services.progressions_service import ProgressionsService

router = APIRouter()

def get_progressions_service(db: Session = Depends(get_db)) -> ProgressionsService:
    """Dependency that provides a ProgressionsService instance."""
    return ProgressionsService(db)

@router.post(
    "/templates/", 
    response_model=ProgressionTemplateResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Create a new progression template",
    response_description="The created progression template"
)
async def create_progression_template(
    template: ProgressionTemplateCreate,
    service: ProgressionsService = Depends(get_progressions_service)
):
    """
    Create a new progression template.
    
    A progression template defines a reusable progression pattern that can be applied to workouts.
    It includes the intensity, effort, sets, and volume calculations.
    
    - **name**: Name of the template (e.g., "5/3/1 BBB")
    - **user_max_id**: ID of the user max this template is based on
    - **intensity**: Intensity as percentage of 1RM (1-100)
    - **effort**: Target RPE (1.0-10.0)
    - **volume**: Optional target reps (will be calculated if not provided)
    """
    try:
        return service.create_progression_template(template)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error creating progression template: {str(e)}"
        )

@router.get(
    "/templates/", 
    response_model=List[ProgressionTemplateResponse],
    summary="List progression templates",
    response_description="List of progression templates"
)
async def list_progression_templates(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, le=1000, description="Maximum number of records to return"),
    user_max_id: Optional[int] = Query(None, description="Filter by user max ID"),
    service: ProgressionsService = Depends(get_progressions_service)
):
    """
    Get a list of progression templates.
    
    Returns a paginated list of progression templates. You can filter by user max ID.
    """
    try:
        return service.list_progression_templates(
            user_max_id=user_max_id,
            skip=skip,
            limit=limit
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error fetching progression templates: {str(e)}"
        )

@router.get(
    "/templates/{template_id}", 
    response_model=ProgressionTemplateResponse,
    summary="Get a progression template by ID",
    response_description="The requested progression template"
)
async def get_progression_template(
    template_id: int,
    service: ProgressionsService = Depends(get_progressions_service)
):
    """
    Get a specific progression template by ID.
    
    Returns the details of a single progression template including related user max 
    and exercise information.
    """
    try:
        return service.get_progression_template(template_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching progression template: {str(e)}"
        )

@router.put(
    "/templates/{template_id}", 
    response_model=ProgressionTemplateResponse,
    summary="Update a progression template",
    response_description="The updated progression template"
)
async def update_progression_template(
    template_id: int,
    template: ProgressionTemplateUpdate,
    service: ProgressionsService = Depends(get_progressions_service)
):
    """
    Update a progression template.
    
    Updates the specified fields of a progression template. If intensity or effort is updated,
    the volume will be automatically recalculated.
    
    - **name**: Optional new name for the template
    - **sets**: Optional new number of sets
    - **intensity**: Optional new intensity percentage (1-100)
    - **effort**: Optional new target RPE (1.0-10.0)
    - **volume**: Optional new target reps (will be recalculated if not provided)
    - **notes**: Optional new notes
    """
    try:
        return service.update_progression_template(template_id, template)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating progression template: {str(e)}"
        )

@router.delete(
    "/templates/{template_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a progression template",
    response_description="Template successfully deleted"
)
async def delete_progression_template(
    template_id: int,
    service: ProgressionsService = Depends(get_progressions_service)
):
    """
    Delete a progression template.
    
    Deletes the specified progression template. Any workouts using this template will have their
    progression_template_id set to NULL.
    """
    try:
        success = service.delete_progression_template(template_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Progression template not found"
            )
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting progression template: {str(e)}"
        )
