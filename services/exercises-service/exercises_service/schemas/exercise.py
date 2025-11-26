from pydantic import BaseModel


class ExerciseExistsResponse(BaseModel):
    exists: bool
