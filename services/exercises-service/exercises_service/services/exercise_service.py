from pathlib import Path
import json
from exercises_service.repositories.exercise_repository import ExerciseRepository

class ExerciseService:
    MUSCLE_LABELS = None
    
    @classmethod
    def load_muscle_metadata(cls):
        if cls.MUSCLE_LABELS is not None:
            return
        current_dir = Path(__file__).resolve().parent
        metadata_path = current_dir / ".." / "muscle_metadata.json"
        try:
            with open(metadata_path, "r") as f:
                data = json.load(f)
            # Валидация структуры
            for muscle_key, muscle_data in data.items():
                if not isinstance(muscle_data, dict):
                    raise ValueError(f"Muscle data for '{muscle_key}' must be a dictionary")
                if "label" not in muscle_data or not isinstance(muscle_data["label"], str):
                    raise ValueError(f"Muscle '{muscle_key}' must have a string 'label'")
                if "group" not in muscle_data or not isinstance(muscle_data["group"], str):
                    raise ValueError(f"Muscle '{muscle_key}' must have a string 'group'")
            cls.MUSCLE_LABELS = data
        except FileNotFoundError:
            # Файл не найден
            cls.MUSCLE_LABELS = {}
            raise
        except json.JSONDecodeError as e:
            # Ошибка формата JSON
            cls.MUSCLE_LABELS = {}
            raise ValueError(f"Invalid JSON in muscle_metadata.json: {e}") from e
        except Exception as e:
            # Другие ошибки
            cls.MUSCLE_LABELS = {}
            raise
