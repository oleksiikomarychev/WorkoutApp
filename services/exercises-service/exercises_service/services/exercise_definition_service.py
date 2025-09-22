from sqlalchemy.ext.asyncio import AsyncSession
from ..repositories.exercise_repository import ExerciseRepository
from .. import schemas

class ExerciseDefinitionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = ExerciseRepository()

    async def list_definitions(self, ids: list[int] | None = None):
        return await self.repository.list_exercise_definitions(self.db, ids)

    async def get_definition(self, exercise_list_id: int):
        return await self.repository.get_exercise_definition(self.db, exercise_list_id)

    async def create_definition(self, exercise: schemas.ExerciseListCreate):
        return await self.repository.create_exercise_definition(self.db, exercise.model_dump())

    async def update_definition(self, exercise_list_id: int, exercise_update: schemas.ExerciseListCreate):
        return await self.repository.update_exercise_definition(self.db, exercise_list_id, exercise_update.model_dump())

    async def delete_definition(self, exercise_list_id: int):
        return await self.repository.delete_exercise_definition(self.db, exercise_list_id)
