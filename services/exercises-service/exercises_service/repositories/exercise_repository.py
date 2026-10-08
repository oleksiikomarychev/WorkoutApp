from exercises_service.models import ExerciseList
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession


class ExerciseRepository:
    @staticmethod
    async def list_exercise_definitions(
        db, 
        ids: list[int] | None = None, 
        limit: int | None = None, 
        offset: int = 0,
        muscle_groups: list[str] | None = None,
        equipment_types: list[str] | None = None,
        search: str | None = None
    ):
        query = select(ExerciseList)
        
        if ids:
            query = query.where(ExerciseList.id.in_(ids))
    
        if muscle_groups:
            query = query.where(ExerciseList.muscle_group.in_(muscle_groups))
 
        if equipment_types:
            query = query.where(ExerciseList.equipment.in_(equipment_types))
    
        if search:
            await db.execute(text("SET LOCAL pg_trgm.similarity_threshold = 0.1"))
            query = query.where(ExerciseList.name.op("%")(search))
            query = query.order_by(ExerciseList.id)
        else:
            query = query.order_by(ExerciseList.id)
    
        if limit:
            query = query.limit(limit).offset(offset)
        
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_exercise_definition(db, exercise_list_id: int):
        return await db.get(ExerciseList, exercise_list_id)

    @staticmethod
    async def get_exercise_definition_by_name(db: AsyncSession, name: str):
        query = select(ExerciseList).where(ExerciseList.name == name)
        result = await db.execute(query)
        return result.scalars().first()

    @staticmethod
    async def get_exercise_definitions_by_names(db: AsyncSession, names: list[str]) -> list[ExerciseList]:
        if not names:
            return []
        query = select(ExerciseList).where(ExerciseList.name.in_(names))
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def batch_upsert_exercise_definitions(db: AsyncSession, exercises: list[dict]) -> list[ExerciseList]:
        if not exercises:
            return []
        
        names = [item.get("name") for item in exercises]
        existing = await ExerciseRepository.get_exercise_definitions_by_names(db, names)
        existing_by_name = {e.name: e for e in existing}

        result_items: list[ExerciseList] = []
        for payload in exercises:
            name = payload.get("name")
            if name in existing_by_name:
                db_item = existing_by_name[name]
                for key, value in payload.items():
                    setattr(db_item, key, value)
                result_items.append(db_item)
            else:
                db_item = ExerciseList(**payload)
                db.add(db_item)
                result_items.append(db_item)

        await db.flush()
        return result_items

    @staticmethod
    async def create_exercise_definition(db, exercise: dict):
        db_exercise = ExerciseList(**exercise)
        db.add(db_exercise)
        await db.flush()
        await db.refresh(db_exercise)
        return db_exercise

    @staticmethod
    async def delete_exercise_definition(db, exercise_list_id: int):
        stmt_definition = delete(ExerciseList).where(ExerciseList.id == exercise_list_id)
        result = await db.execute(stmt_definition)
        await db.flush()
        return result.rowcount > 0

    @staticmethod
    async def update_exercise_definition(db, db_exercise, update_data: dict):
        if isinstance(db_exercise, int):
            db_exercise = await ExerciseRepository.get_exercise_definition(db, db_exercise)
            if not db_exercise:
                raise ValueError(f"Exercise definition with id {db_exercise} not found")

        for key, value in update_data.items():
            setattr(db_exercise, key, value)
        await db.flush()
        await db.refresh(db_exercise)
        return db_exercise

