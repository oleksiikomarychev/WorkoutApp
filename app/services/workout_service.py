from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.models.exercises import ExerciseInstance


class WorkoutService:
    @staticmethod
    def get_exercise_instance_dict(exercise_instance: ExerciseInstance) -> Dict[str, Any]:
        result = {
            'id': exercise_instance.id,
            'exercise_list_id': exercise_instance.exercise_list_id,
            'workout_id': exercise_instance.workout_id,
            'user_max_id': exercise_instance.user_max_id,
            'weight': exercise_instance.weight,
            'sets': exercise_instance.sets,
            'exercise': {
                'id': exercise_instance.exercise_definition.id,
                'name': exercise_instance.exercise_definition.name,
                'muscle_group': exercise_instance.exercise_definition.muscle_group,
                'equipment': exercise_instance.exercise_definition.equipment
            } if exercise_instance.exercise_definition else None,
            'user_max': {
                'id': exercise_instance.user_max.id,
                'max_weight': exercise_instance.user_max.max_weight,
                'rep_max': exercise_instance.user_max.rep_max
            } if exercise_instance.user_max else None
        }
        return result
