from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict, Any
from app.workout_models import ProgressionTemplate, UserMax, Workout, ExerciseInstance, ExerciseInstanceWithProgressionTemplate
from app.workout_schemas import ProgressionTemplateCreate


class ProgressionsRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_progression_templates(
        self, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[ProgressionTemplate]:
        return (
            self.db.query(ProgressionTemplate)
            .options(
                joinedload(ProgressionTemplate.exercise_instances)
                .joinedload(ExerciseInstanceWithProgressionTemplate.exercise_list)
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_progression_template_by_id(self, template_id: int) -> Optional[ProgressionTemplate]:
        return (
            self.db.query(ProgressionTemplate)
            .options(
                joinedload(ProgressionTemplate.exercise_instances)
                .joinedload(ExerciseInstanceWithProgressionTemplate.exercise_list)
            )
            .filter(ProgressionTemplate.id == template_id)
            .first()
        )
    
    def create_progression_template(self, template_data: Dict[str, Any]) -> ProgressionTemplate:
        db_template = ProgressionTemplate(**template_data)
        self.db.add(db_template)
        self.db.commit()
        self.db.refresh(db_template)
        return db_template
    
    def update_progression_template(
        self, 
        db_template: ProgressionTemplate,
        template_data: Dict[str, Any]
    ) -> ProgressionTemplate:
        for key, value in template_data.items():
            setattr(db_template, key, value)
            
        self.db.commit()
        self.db.refresh(db_template)
        return db_template
    
    def delete_progression_template(self, template: ProgressionTemplate) -> bool:
        try:
            self.db.query(Workout).filter(
                Workout.progression_template_id == template.id
            ).update({
                Workout.progression_template_id: None
            })
            
            self.db.delete(template)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise e
    
    def get_template_usage_count(self, template_id: int) -> int:
        return self.db.query(Workout).filter(
            Workout.progression_template_id == template_id
        ).count()
