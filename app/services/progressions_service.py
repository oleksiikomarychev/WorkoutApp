from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.progressions_repository import ProgressionsRepository
from app.repositories.user_max_repository import UserMaxRepository
from app.workout_models import ProgressionTemplate, UserMax, Workout
from app.workout_schemas import (
    ProgressionTemplateCreate, 
    ProgressionTemplateUpdate,
    ProgressionTemplateResponse,
    UserMax as UserMaxSchema
)


class ProgressionsService:

    def __init__(self, db: Session):
        """Initialize the service with a database session."""
        self.db = db
        self.progressions_repo = ProgressionsRepository(db)
        self.user_max_repo = UserMaxRepository(db)
    
    def create_progression_template(
        self, 
        template_data: ProgressionTemplateCreate
    ) -> ProgressionTemplateResponse:
        """Create a new progression template with validation.
        
        Args:
            template_data: The template data to create
            
        Returns:
            The created ProgressionTemplateResponse with calculated values
            
        Raises:
            HTTPException: If validation fails or user max is not found
        """
        user_max = self.user_max_repo.get_user_max_by_id(template_data.user_max_id)
        if not user_max:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User max with id {template_data.user_max_id} not found"
            )
        
        template_dict = template_data.model_dump()
        db_template = self.progressions_repo.create_progression_template(template_dict)
        
        return self._format_template_response(db_template)
    
    def get_progression_template(
        self, 
        template_id: int
    ) -> ProgressionTemplateResponse:
        """Get a single progression template by ID.
        
        Args:
            template_id: ID of the template to retrieve
            
        Returns:
            The requested ProgressionTemplateResponse
            
        Raises:
            HTTPException: If template not found
        """
        db_template = self.progressions_repo.get_progression_template_by_id(template_id)
        if not db_template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Progression template with id {template_id} not found"
            )
            
        return self._format_template_response(db_template)
    
    def list_progression_templates(
        self, 
        user_max_id: Optional[int] = None,
        skip: int = 0, 
        limit: int = 100
    ) -> List[ProgressionTemplateResponse]:
        """List progression templates with optional filtering.
        
        Args:
            user_max_id: Optional filter by user max ID
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return (pagination)
            
        Returns:
            List of ProgressionTemplateResponse objects
        """
        templates = self.progressions_repo.get_progression_templates(
            skip=skip,
            limit=limit,
            user_max_id=user_max_id
        )
        
        return [self._format_template_response(t) for t in templates]
    
    def update_progression_template(
        self, 
        template_id: int,
        template_data: ProgressionTemplateUpdate
    ) -> ProgressionTemplateResponse:
        """Update an existing progression template.
        
        Args:
            template_id: ID of the template to update
            template_data: The updated template data
            
        Returns:
            The updated ProgressionTemplateResponse
            
        Raises:
            HTTPException: If template not found
        """
        db_template = self.progressions_repo.get_progression_template_by_id(template_id)
        if not db_template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Progression template with id {template_id} not found"
            )
        
        if template_data.user_max_id and template_data.user_max_id != db_template.user_max_id:
            new_user_max = self.user_max_repo.get_user_max_by_id(template_data.user_max_id)
            if not new_user_max:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User max with id {template_data.user_max_id} not found"
                )
        
        update_data = template_data.model_dump(exclude_unset=True)
        updated_template = self.progressions_repo.update_progression_template(
            db_template, 
            update_data
        )
        
        return self._format_template_response(updated_template)
    
    def delete_progression_template(
        self, 
        template_id: int
    ) -> bool:
        db_template = self.progressions_repo.get_progression_template_by_id(template_id)
        if not db_template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Progression template with id {template_id} not found"
            )
            
        return self.progressions_repo.delete_progression_template(db_template)
    
    def _format_template_response(
        self, 
        template: ProgressionTemplate
    ) -> ProgressionTemplateResponse:
        """Format a ProgressionTemplate for API response.
        
        Args:
            template: The ProgressionTemplate to format
            
        Returns:
            Formatted ProgressionTemplateResponse
        """
        user_max = self.user_max_repo.get_user_max_by_id(template.user_max_id)
        
        if not user_max:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Associated user max not found for template {template.id}"
            )
        
        calculated_weight = round((template.intensity / 100) * user_max.max_weight, 1)
        
        return ProgressionTemplateResponse(
            **template.__dict__,
            calculated_weight=calculated_weight,
        )
    
    def _calculate_effort(self, intensity: int, volume: int) -> float:
        """Calculate RPE based on intensity and volume.
        
        Args:
            intensity: Percentage of 1RM (1-100)
            volume: Number of reps
            
        Returns:
            Estimated RPE (1.0-10.0)
        """
        if intensity >= 90:
            return 9.0 if volume <= 3 else 9.5
        elif intensity >= 80:
            if volume <= 3: return 8.0
            elif volume <= 5: return 8.5
            else: return 9.0
        elif intensity >= 70:
            if volume <= 5: return 7.0
            elif volume <= 8: return 7.5
            else: return 8.0
        else:
            if volume <= 8: return 6.0
            elif volume <= 10: return 6.5
            else: return 7.0

    def _estimate_volume(self, intensity: int, effort: float) -> int:
        """Estimate volume based on intensity and RPE.
        
        Args:
            intensity: Percentage of 1RM (1-100)
            effort: RPE (1.0-10.0)
            
        Returns:
            Estimated number of reps
        """
        if intensity >= 90:
            if effort <= 8.0: return 1
            elif effort <= 8.5: return 2
            else: return 3
        elif intensity >= 80:
            if effort <= 7.5: return 3
            elif effort <= 8.0: return 4
            elif effort <= 8.5: return 5
            else: return 6
        elif intensity >= 70:
            if effort <= 7.0: return 6
            elif effort <= 7.5: return 7
            elif effort <= 8.0: return 8
            else: return 9
        else:
            if effort <= 6.5: return 9
            elif effort <= 7.0: return 10
            else: return 12

    def _estimate_intensity(self, effort: float, volume: int) -> int:
        """Estimate intensity based on RPE and volume.
        
        Args:
            effort: RPE (1.0-10.0)
            volume: Number of reps
            
        Returns:
            Estimated percentage of 1RM (1-100)
        """
        if volume <= 3:
            if effort <= 8.0: return 90
            elif effort <= 8.5: return 87
            else: return 84
        elif volume <= 5:
            if effort <= 7.5: return 85
            elif effort <= 8.0: return 82
            elif effort <= 8.5: return 80
            else: return 77
        elif volume <= 8:
            if effort <= 7.0: return 80
            elif effort <= 7.5: return 77
            elif effort <= 8.0: return 75
            else: return 72
        else:
            if effort <= 6.5: return 70
            elif effort <= 7.0: return 67
            else: return 65
        if data.get('volume') is not None and data.get('effort') is None and 'intensity' in data:
            data['effort'] = self._calculate_effort(data['intensity'], data['volume'])
        updated_template = self.repository.update_progression_template(template, data)
        if not hasattr(updated_template, 'user_max') or updated_template.user_max is None:
            raise HTTPException(
                status_code=404,
                detail=f"User max not found for progression {template_id}"
            )
        return self._prepare_progression_response(updated_template, updated_template.user_max)
    
    def delete_progression_template(self, template_id: int) -> Dict[str, str]:
        db_template = self.progressions_repo.get_progression_template_by_id(template_id)
        if not db_template:
            raise HTTPException(status_code=404, detail="Progression template not found")
        self.progressions_repo.delete_progression_template(db_template)
        return {"detail": "Progression template deleted"}