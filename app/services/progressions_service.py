from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.progressions_repository import ProgressionsRepository
from app.repositories.user_max_repository import UserMaxRepository
from app.workout_models import (
    ProgressionTemplate, 
    ExerciseInstanceWithProgressionTemplate as models_ExerciseInstanceWithProgressionTemplate,
    UserMax,
    Workout,
    ExerciseList
)
from app.workout_calculation import WorkoutCalculator
from app.workout_schemas import (
    ProgressionTemplateCreate, 
    ProgressionTemplateUpdate,
    ProgressionTemplateResponse,
    ExerciseInstanceWithProgressionTemplate,
    ExerciseInstanceWithProgressionTemplateUpdate,
    UserMax as UserMaxSchema
)


class ProgressionsService:

    def __init__(self, db: Session):
        """Initialize the service with a database session."""
        self.db = db
        self.progressions_repo = ProgressionsRepository(db)
        self.user_max_repo = UserMaxRepository(db)
    
    def create_progression_template(self, template_data: ProgressionTemplateCreate) -> ProgressionTemplateResponse:
        template_dict = template_data.model_dump()
        db_template = self.progressions_repo.create_progression_template(template_dict)
        
        return self._format_template_response(db_template)
    
    def get_progression_template(self, template_id: int) -> ProgressionTemplateResponse:
        db_template = self.progressions_repo.get_progression_template_by_id(template_id)
        if not db_template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Progression template with id {template_id} not found"
            )
            
        return self._format_template_response(db_template)
    
    def list_progression_templates(
        self,
        skip: int = 0, 
        limit: int = 100
    ) -> List[ProgressionTemplateResponse]:
        """List progression templates.
        
        Args:
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return (pagination)
            
        Returns:
            List of ProgressionTemplateResponse objects
        """
        templates = self.progressions_repo.get_progression_templates(
            skip=skip,
            limit=limit
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
        
        update_data = template_data.model_dump(exclude_unset=True)
        updated_template = self.progressions_repo.update_progression_template(
            db_template, 
            update_data
        )
        
        return self._format_template_response(updated_template)
    
    def delete_progression_template(self, template_id: int) -> None:
        db_template = self.progressions_repo.get_progression_template_by_id(template_id)
        if not db_template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Progression template with id {template_id} not found"
            )
        
        self.progressions_repo.delete_progression_template(db_template)
        self.db.commit()

    def create_progression_instance(self, template_id: int, exercise_list_id: int, instance_data: ExerciseInstanceWithProgressionTemplate) -> models_ExerciseInstanceWithProgressionTemplate:
        db_template = self.progressions_repo.get_progression_template_by_id(template_id)
        db_exercise_list = self.db.get(ExerciseList, exercise_list_id)
        if not db_template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Progression template with id {template_id} not found"
            )
        if not db_exercise_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Exercise list with id {exercise_list_id} not found"
            )
            
        # Process each set in the request
        processed_sets = []
        for set_data in instance_data.sets:
            intensity = set_data.intensity
            volume = set_data.volume
            effort = set_data.effort
            
            # Calculate missing parameters if we have two out of three
            if intensity is None and effort is not None and volume is not None:
                intensity = WorkoutCalculator.get_intensity(volume, effort)
            elif effort is None and intensity is not None and volume is not None:
                effort = WorkoutCalculator.get_effort(volume, intensity)
            elif volume is None and intensity is not None and effort is not None:
                volume = WorkoutCalculator.get_volume(intensity, effort)
            
            # Add the set to the list
            processed_sets.append({
                'intensity': intensity,
                'volume': volume,
                'effort': effort
            })
        
        # Create the instance data
        instance_data = {
            'progression_template_id': db_template.id,
            'exercise_list_id': exercise_list_id,
            'sets': processed_sets
        }
        
        # Create the instance
        db_instance = models_ExerciseInstanceWithProgressionTemplate(**instance_data)
        self.db.add(db_instance)
        self.db.commit()
        self.db.refresh(db_instance)
        return db_instance

    def get_progression_instance(self, template_id: int, instance_id: int) -> models_ExerciseInstanceWithProgressionTemplate:
        db_instance = self.db.query(models_ExerciseInstanceWithProgressionTemplate).filter(
            models_ExerciseInstanceWithProgressionTemplate.id == instance_id,
            models_ExerciseInstanceWithProgressionTemplate.progression_template_id == template_id
        ).first()
        
        if not db_instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Progression instance with id {instance_id} not found for template {template_id}"
            )
        
        return db_instance

    def list_progression_instances(self, template_id: int, skip: int = 0, limit: int = 100) -> List[ExerciseInstanceWithProgressionTemplate]:
        db_template = self.progressions_repo.get_progression_template_by_id(template_id)
        if not db_template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Progression template with id {template_id} not found"
            )
            
        return self.db.query(models_ExerciseInstanceWithProgressionTemplate).filter(
            models_ExerciseInstanceWithProgressionTemplate.progression_template_id == template_id
        ).offset(skip).limit(limit).all()

    def update_progression_instance(
        self,
        template_id: int,
        instance_id: int,
        exercise_list_id: int,
        instance_data: ExerciseInstanceWithProgressionTemplateUpdate
    ) -> models_ExerciseInstanceWithProgressionTemplate:
        db_instance = self.db.query(models_ExerciseInstanceWithProgressionTemplate).filter(
            models_ExerciseInstanceWithProgressionTemplate.id == instance_id,
            models_ExerciseInstanceWithProgressionTemplate.progression_template_id == template_id
        ).first()
        if not db_instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Progression instance with id {instance_id} not found for template {template_id}"
            )
        
        db_exercise_list = self.db.get(ExerciseList, exercise_list_id)
        if not db_exercise_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Exercise list with id {exercise_list_id} not found"
            )
        
        # If sets are being updated
        if instance_data.sets is not None:
            processed_sets = []
            for set_data in instance_data.sets:
                intensity = set_data.intensity
                volume = set_data.volume
                effort = set_data.effort
                
                # Calculate missing parameters if we have two out of three
                if intensity is None and effort is not None and volume is not None:
                    intensity = WorkoutCalculator.get_intensity(volume, effort)
                elif effort is None and intensity is not None and volume is not None:
                    effort = WorkoutCalculator.get_effort(volume, intensity)
                elif volume is None and intensity is not None and effort is not None:
                    volume = WorkoutCalculator.get_volume(intensity, effort)
                
                # Add the set to the list
                processed_sets.append({
                    'intensity': intensity,
                    'volume': volume,
                    'effort': effort
                })
            
            # Update the instance with the new sets
            db_instance.sets = processed_sets
        
        # Update exercise list if needed
        if exercise_list_id != db_instance.exercise_list_id:
            db_instance.exercise_list_id = exercise_list_id
        
        self.db.commit()
        self.db.refresh(db_instance)
        return db_instance

    def delete_progression_instance(self, template_id: int, instance_id: int) -> None:
        db_instance = self.db.query(models_ExerciseInstanceWithProgressionTemplate).filter(
            models_ExerciseInstanceWithProgressionTemplate.id == instance_id,
            models_ExerciseInstanceWithProgressionTemplate.progression_template_id == template_id
        ).first()
        
        if not db_instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Progression instance with id {instance_id} not found for template {template_id}"
            )

        self.db.delete(db_instance)
        self.db.commit()

    def _format_template_response(self, template: ProgressionTemplate) -> ProgressionTemplateResponse:
        """Format a ProgressionTemplate for response."""
        
        # Get the first exercise instance with this template
        if template.exercise_instances:
            instance_with_template = template.exercise_instances[0]
            exercise_list = instance_with_template.exercise_list
            
            
        return ProgressionTemplateResponse(
            id=template.id,
            name=template.name,
            intensity=None if not template.exercise_instances else template.exercise_instances[0].intensity,
            effort=None if not template.exercise_instances else template.exercise_instances[0].effort,
            volume=None if not template.exercise_instances else template.exercise_instances[0].volume,
        )