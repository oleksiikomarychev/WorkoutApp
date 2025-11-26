from fastapi import HTTPException, status


class NotFoundException(HTTPException):
    def __init__(self, detail: str = "Объект не найден"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class WorkoutNotFoundException(NotFoundException):
    def __init__(self, workout_id: int):
        super().__init__(detail=f"Тренировка с id={workout_id} не найдена")


class SessionNotFoundException(NotFoundException):
    def __init__(self, session_id: int):
        super().__init__(detail=f"Сессия с id={session_id} не найдена")


class ActiveSessionNotFoundException(NotFoundException):
    def __init__(self, workout_id: int):
        super().__init__(detail=f"Активная сессия для тренировки с id={workout_id} не найдена")
