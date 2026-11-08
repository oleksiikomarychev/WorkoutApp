from __future__ import annotations

import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any

from fastapi import HTTPException

from exercises_service.services.exercise_definition_service import ExerciseDefinitionService


def validate_exercise_definition(exercise_id_param: str = "exercise_list_id") -> Callable[..., Any]:
    """Decorator validating existence of exercise definition before route execution."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            exercise_id = kwargs.get(exercise_id_param)
            if exercise_id is None:
                sig = inspect.signature(func)
                param_names = list(sig.parameters.keys())
                if exercise_id_param in param_names:
                    param_index = param_names.index(exercise_id_param)
                    if param_index < len(args):
                        exercise_id = args[param_index]

            if exercise_id is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required parameter: {exercise_id_param}",
                )

            db = kwargs.get("db")
            if db is None:
                sig = inspect.signature(func)
                param_names = list(sig.parameters.keys())
                if "db" in param_names:
                    param_index = param_names.index("db")
                    if param_index < len(args):
                        db = args[param_index]

            if not db:
                raise HTTPException(
                    status_code=500,
                    detail="Database session not found",
                )

            redis_client = kwargs.get("redis_client")
            service = ExerciseDefinitionService(db, redis_client)
            definition = await service.get_definition(exercise_id)
            if not definition:
                raise HTTPException(
                    status_code=404,
                    detail="Exercise definition not found",
                )

            kwargs["_exercise_definition"] = definition

            return await func(*args, **kwargs)

        return wrapper

    return decorator
