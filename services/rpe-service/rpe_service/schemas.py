from pydantic import BaseModel, Field
from typing import Optional, Literal

class RpeComputeRequest(BaseModel):
    """Request to compute set params from RPE.
    Provide any two of: intensity (1-100), effort (1-10), volume (reps >=1).
    Optionally provide max_weight (interpreted as 1RM) to compute working weight.
    """
    intensity: Optional[int] = Field(default=None, ge=1, le=100)
    effort: Optional[int] = Field(default=None, ge=1, le=10)
    volume: Optional[int] = Field(default=None, ge=1)

    # Сервис не хранит состояние и не обращается к БД.
    # Для расчетов с использованием 1ПМ передавайте значение в поле max_weight
    # или user_max_id для автоматического получения 1ПМ из user-max-service.
    max_weight: Optional[float] = Field(default=None, ge=0)
    user_max_id: Optional[int] = Field(default=None, description="ID пользовательского 1ПМ в user-max-service")
    rounding_step: float = Field(default=2.5, gt=0)
    rounding_mode: Literal['nearest', 'floor', 'ceil'] = Field(default='nearest')

class ComputationError(BaseModel):
    error: str
    message: str

class RpeComputeResponse(BaseModel):
    intensity: Optional[int] = None
    effort: Optional[int] = None
    volume: Optional[int] = None
    weight: Optional[int] = None
