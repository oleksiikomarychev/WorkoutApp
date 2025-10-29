from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from ..repositories.exercise_repository import ExerciseRepository
from .set_service import SetService
from .. import schemas
import logging

logger = logging.getLogger(__name__)

class ExerciseInstanceService:
    def __init__(self, db: AsyncSession, set_service: SetService, user_id: str):
        self.db = db
        self.set_service = set_service
        self.repository = ExerciseRepository()
        self.user_id = user_id

    async def create_instance(self, workout_id: int, instance_data: schemas.ExerciseInstanceCreate) -> dict:
        logger.info(f"1. Получен запрос на создание экземпляра упражнения для workout_id={workout_id}")
        logger.info(f"instance_data={instance_data}")
        
        # Проверяем существование определения упражнения
        logger.info(f"2. Проверяем определение упражнения id={instance_data.exercise_list_id}")
        definition = await ExerciseRepository.get_exercise_definition(self.db, instance_data.exercise_list_id)
        if not definition:
            logger.error(f"Определение упражнения id={instance_data.exercise_list_id} не найдено")
            raise ValueError(f"Exercise definition with id {instance_data.exercise_list_id} not found")
        
        logger.info("3. Подготавливаем данные")
        instance_dict = instance_data.model_dump()
        instance_dict["workout_id"] = workout_id
        instance_dict["user_id"] = self.user_id
        if 'sets' in instance_dict:
            instance_dict['sets'] = self.set_service.prepare_sets(instance_dict['sets'])
        logger.info(f"4. Данные для создания: {instance_dict}")
        
        logger.info("5. Создаём экземпляр в БД")
        result = await self.repository.create_exercise_instance(self.db, instance_dict)
        logger.info(f"6. Результат создания: {result}")
        
        return result

    async def update_instance(self, instance_id: int, update_data: schemas.ExerciseInstanceBase) -> dict:
        db_instance = await self.repository.get_exercise_instance(self.db, instance_id, self.user_id)
        if not db_instance:
            raise ValueError("Exercise instance not found")
        update_dict = update_data.model_dump(exclude_unset=True)
        if "sets" in update_dict:
            update_dict["sets"] = self.set_service.prepare_sets(update_dict["sets"])
        return await self.repository.update_exercise_instance(self.db, db_instance, update_dict)

    async def update_set(self, instance_id: int, set_id: int, update_data: dict) -> dict:
        """
        Обновляет конкретный сет в экземпляре упражнения
        """
        db_instance = await self.repository.get_exercise_instance(self.db, instance_id, self.user_id)
        if not db_instance:
            raise ValueError("Exercise instance not found")
        if not isinstance(db_instance.sets, list):
            raise ValueError("No sets to update")

        # Синхронизация полей усилия: если приходит только одно из полей, зеркалим во второе
        try:
            if "rpe" in update_data and "effort" not in update_data:
                update_data["effort"] = update_data.get("rpe")
            if "effort" in update_data and "rpe" not in update_data:
                update_data["rpe"] = update_data.get("effort")
        except Exception:
            # best-effort only
            pass

        # Обновляем сет
        new_sets = self.set_service.update_set(db_instance.sets, set_id, update_data)
        
        # Обновляем экземпляр упражнения
        updated_instance = await self.repository.update_exercise_instance(
            self.db, db_instance, {"sets": new_sets}
        )
        return {
            "id": updated_instance.id,
            "exercise_list_id": updated_instance.exercise_list_id,
            "sets": self.set_service.normalize_sets_for_frontend(updated_instance.sets or []),
            "notes": updated_instance.notes,
            "order": updated_instance.order,
            "workout_id": updated_instance.workout_id,
            "user_max_id": updated_instance.user_max_id
        }
