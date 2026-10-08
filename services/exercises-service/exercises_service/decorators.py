import inspect
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec

from fastapi import HTTPException

from exercises_service.services.exercise_definition_service import ExerciseDefinitionService


def validate_exercise_definition(exercise_id_param: str = "exercise_list_id"):
    def decorator(func: Callable[ParamSpec, ...]) -> Callable[ParamSpec, ...]:
        @wraps(func)
        async def wrapper(*args: ParamSpec.args, **kwargs: ParamSpec.kwargs):
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
                    detail=f"Missing required parameter: {exercise_id_param}"
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
                    detail="Database session not found"
                )
            
            service = ExerciseDefinitionService(db)
            definition = await service.get_definition(exercise_id)
            if not definition:
                raise HTTPException(
                    status_code=404, 
                    detail="Exercise definition not found"
                )
            
            kwargs["_exercise_definition"] = definition
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
