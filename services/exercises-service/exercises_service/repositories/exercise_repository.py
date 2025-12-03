from exercises_service.models import ExerciseInstance, ExerciseList
from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class ExerciseRepository:
    @staticmethod
    async def list_exercise_definitions(db, ids: list[int] | None = None):
        query = select(ExerciseList)
        if ids:
            query = query.where(ExerciseList.id.in_(ids))
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_exercise_instance(db: AsyncSession, instance_id: int, user_id: str):
        query = (
            select(ExerciseInstance)
            .options(selectinload(ExerciseInstance.exercise_definition))
            .where(
                and_(
                    ExerciseInstance.id == instance_id,
                    ExerciseInstance.user_id == user_id,
                )
            )
        )
        result = await db.execute(query)
        return result.scalars().first()

    @staticmethod
    async def get_exercise_definition(db, exercise_list_id: int):
        return await db.get(ExerciseList, exercise_list_id)

    @staticmethod
    async def create_exercise_definition(db, exercise: dict):
        db_exercise = ExerciseList(**exercise)
        db.add(db_exercise)
        await db.commit()
        await db.refresh(db_exercise)
        return db_exercise

    @staticmethod
    async def create_exercise_instance(db: AsyncSession, instance_data: dict):
        db_instance = ExerciseInstance(**instance_data)
        db.add(db_instance)
        await db.commit()
        await db.refresh(db_instance)
        return db_instance

    @staticmethod
    async def update_exercise_instance(db: AsyncSession, db_instance: ExerciseInstance, update_data: dict):
        for key, value in update_data.items():
            setattr(db_instance, key, value)
        await db.commit()
        await db.refresh(db_instance)
        return db_instance

    @staticmethod
    async def delete_exercise_instance(db: AsyncSession, instance_id: int, user_id: str):
        query = select(ExerciseInstance).where(
            and_(
                ExerciseInstance.id == instance_id,
                ExerciseInstance.user_id == user_id,
            )
        )
        result = await db.execute(query)
        db_instance = result.scalars().first()
        if db_instance:
            db.delete(db_instance)
            await db.commit()

    @staticmethod
    async def delete_exercise_definition(db, exercise_list_id: int):
        # Удаляем все связанные экземпляры упражнений
        stmt_instances = delete(ExerciseInstance).where(ExerciseInstance.exercise_list_id == exercise_list_id)
        await db.execute(stmt_instances)

        # Удаляем само определение
        stmt_definition = delete(ExerciseList).where(ExerciseList.id == exercise_list_id)
        result = await db.execute(stmt_definition)
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def update_exercise_definition(db, db_exercise, update_data: dict):
        # If db_exercise is an integer (ID), fetch the actual ORM object
        if isinstance(db_exercise, int):
            db_exercise = await ExerciseRepository.get_exercise_definition(db, db_exercise)
            if not db_exercise:
                raise ValueError(f"Exercise definition with id {db_exercise} not found")

        for key, value in update_data.items():
            setattr(db_exercise, key, value)
        await db.commit()
        await db.refresh(db_exercise)
        return db_exercise

    @staticmethod
    async def get_instances_by_workout(db: AsyncSession, workout_id: int, user_id: str):
        result = await db.execute(
            select(ExerciseInstance)
            .options(selectinload(ExerciseInstance.exercise_definition))
            .filter(
                and_(
                    ExerciseInstance.workout_id == workout_id,
                    ExerciseInstance.user_id == user_id,
                )
            )
        )
        return result.scalars().all()

    @staticmethod
    async def migrate_set_ids(db):
        from exercises_service.services.exercise_service import ExerciseService

        updated = 0
        query = select(ExerciseInstance)
        result = await db.execute(query)
        instances = result.scalars().all()
        for inst in instances:
            if isinstance(inst.sets, list) and any(
                not isinstance(s, dict) or "id" not in s or not isinstance(s.get("id"), int) for s in inst.sets
            ):
                inst.sets = ExerciseService.ensure_set_ids(inst.sets)
                updated += 1
        if updated:
            await db.commit()
        return {"updated_instances": updated}

    @staticmethod
    async def create_exercise_instances_batch(db: AsyncSession, instances_data: list, user_id: str):
        from exercises_service.services.exercise_service import ExerciseService

        created_instances = []
        for data in instances_data:
            instance_dict = dict(data)
            if "sets" in instance_dict:
                instance_dict["sets"] = ExerciseService.ensure_set_ids(instance_dict["sets"])
            instance_dict["user_id"] = user_id
            db_instance = ExerciseInstance(**instance_dict)
            db.add(db_instance)
            await db.flush()
            created_instances.append(
                {
                    "id": db_instance.id,
                    "exercise_list_id": db_instance.exercise_list_id,
                    "sets": ExerciseService.normalize_sets_for_frontend(db_instance.sets or []),
                    "notes": db_instance.notes,
                    "order": db_instance.order,
                    "workout_id": db_instance.workout_id,
                    "user_max_id": db_instance.user_max_id,
                    "user_id": db_instance.user_id,
                }
            )
        await db.commit()
        return created_instances
