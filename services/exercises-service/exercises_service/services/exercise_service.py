import asyncio
import json
from pathlib import Path

import aiofiles


class ExerciseService:
    MUSCLE_LABELS = None
    _lock = asyncio.Lock()
    _validated = False

    @classmethod
    async def load_muscle_metadata(cls):
        if cls.MUSCLE_LABELS is not None:
            return
        
        async with cls._lock:
            if cls.MUSCLE_LABELS is not None:
                return
            
            current_dir = Path(__file__).resolve().parent
            metadata_path = current_dir / ".." / "muscle_metadata.json"
            
            try:
                async with aiofiles.open(metadata_path) as f:
                    content = await f.read()
                
                data = json.loads(content)

                if not cls._validated:
                    cls._validate_muscle_data(data)
                    cls._validated = True
                
                cls.MUSCLE_LABELS = data
                
            except FileNotFoundError:
                cls.MUSCLE_LABELS = {}
                raise
            except json.JSONDecodeError as e:
                cls.MUSCLE_LABELS = {}
                raise ValueError(f"Invalid data format in muscle_metadata.json: {e}") from e

    @classmethod
    def _validate_muscle_data(cls, data):
        required_fields = {"label": str, "group": str}
        
        for muscle_key, muscle_data in data.items():
            if not isinstance(muscle_data, dict):
                raise ValueError(f"Muscle data for '{muscle_key}' must be a dictionary")
            
            for field, field_type in required_fields.items():
                if field not in muscle_data or not isinstance(muscle_data[field], field_type):
                    raise ValueError(f"Muscle '{muscle_key}' must have a {field_type.__name__} '{field}'")
