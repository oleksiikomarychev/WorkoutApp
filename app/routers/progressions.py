from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from app.services.progressions_service import ProgressionsService
from app.dependencies import get_progressions_service
from app.workout_schemas import (
    ProgressionTemplateCreate,
    ProgressionTemplateUpdate,
    ProgressionTemplateResponse,
    ExerciseInstanceWithProgressionTemplate,
    ExerciseInstanceWithProgressionTemplateUpdate
)

router = APIRouter()

@router.post( "/templates/",  response_model=ProgressionTemplateResponse,  status_code=status.HTTP_201_CREATED, summary="Create a new progression template", response_description="The created progression template")
async def create_progression_template( template: ProgressionTemplateCreate, service: ProgressionsService = Depends(get_progressions_service)):
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
    service: ProgressionsService = Depends(get_progressions_service)
):
    try:
        return service.list_progression_templates(
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
    try:
        return service.update_progression_template(template_id, template)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating progression template: {str(e)}"
        )

@router.get(
    "/templates/{template_id}/instances/",
    response_model=List[ExerciseInstanceWithProgressionTemplate],
    summary="List progression instances"
)
async def list_progression_instances(
    template_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    service: ProgressionsService = Depends(get_progressions_service)
):
    try:
        return service.list_progression_instances(template_id, skip, limit)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching progression instances: {str(e)}"
        )

@router.post(
    "/templates/{template_id}/instances/",
    response_model=ExerciseInstanceWithProgressionTemplate,
    status_code=status.HTTP_201_CREATED,
    summary="Create a progression instance"
)
async def create_progression_instance(
    template_id: int,
    exercise_list_id: int,
    instance_data: ExerciseInstanceWithProgressionTemplate,
    service: ProgressionsService = Depends(get_progressions_service)
):
    try:
        return service.create_progression_instance(template_id, exercise_list_id, instance_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating progression instance: {str(e)}"
        )

@router.put(
    "/templates/{template_id}/instances/{instance_id}",
    response_model=ExerciseInstanceWithProgressionTemplate,
    summary="Update a progression instance"
)
async def update_progression_instance(
    template_id: int,
    instance_id: int,
    exercise_list_id: int,
    instance_data: ExerciseInstanceWithProgressionTemplateUpdate,
    service: ProgressionsService = Depends(get_progressions_service)
):
    try:
        return service.update_progression_instance(template_id, instance_id, exercise_list_id, instance_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating progression instance: {str(e)}"
        )

@router.delete(
    "/templates/{template_id}/instances/{instance_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a progression instance",
    response_description="Instance successfully deleted"
)
async def delete_progression_instance(
    template_id: int,
    instance_id: int,
    service: ProgressionsService = Depends(get_progressions_service)
):
    try:
        success = service.delete_progression_instance(template_id, instance_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Progression instance not found"
            )
        return {"detail": "Progression instance deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting progression instance: {str(e)}"
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
    try:
        success = service.delete_progression_template(template_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Progression template not found"
            )
        return {"detail": "Progression template deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting progression template: {str(e)}"
        )
