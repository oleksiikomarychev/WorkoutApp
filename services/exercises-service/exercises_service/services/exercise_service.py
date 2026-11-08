from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import aiofiles
import structlog

logger = structlog.get_logger(__name__)


class ExerciseService:
    """Service responsible for loading and validating static muscle metadata."""

    MUSCLE_LABELS: dict[str, dict[str, str]] | None = None
    _lock: asyncio.Lock = asyncio.Lock()
    _validated: bool = False

    @classmethod
    async def load_muscle_metadata(cls) -> None:
        """Load and validate muscle metadata from JSON file asynchronously."""
        if cls.MUSCLE_LABELS is not None:
            return

        async with cls._lock:
            if cls.MUSCLE_LABELS is not None:
                return

            current_dir = Path(__file__).resolve().parent
            metadata_path = (current_dir / ".." / "muscle_metadata.json").resolve()

            try:
                async with aiofiles.open(metadata_path, encoding="utf-8") as f:
                    content = await f.read()

                data = json.loads(content)

                if not cls._validated:
                    cls._validate_muscle_data(data)
                    cls._validated = True

                cls.MUSCLE_LABELS = data
                logger.info("Muscle metadata loaded", count=len(data))

            except FileNotFoundError:
                cls.MUSCLE_LABELS = {}
                logger.warning("muscle_metadata.json not found", path=str(metadata_path))
            except json.JSONDecodeError as e:
                cls.MUSCLE_LABELS = {}
                logger.error("Invalid json in muscle_metadata.json", error=str(e))
                raise ValueError(f"Invalid data format in muscle_metadata.json: {e}") from e

    @classmethod
    def _validate_muscle_data(cls, data: Any) -> None:
        """Validate structure of muscle metadata dictionary."""
        if not isinstance(data, dict):
            raise ValueError("Muscle metadata must be a dictionary")

        required_fields = {"label": str, "group": str}

        for muscle_key, muscle_data in data.items():
            if not isinstance(muscle_data, dict):
                raise ValueError(f"Muscle data for '{muscle_key}' must be a dictionary")

            for field, field_type in required_fields.items():
                if field not in muscle_data or not isinstance(muscle_data[field], field_type):
                    raise ValueError(f"Muscle '{muscle_key}' must have a {field_type.__name__} '{field}'")
