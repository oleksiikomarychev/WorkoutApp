from pydantic import BaseModel, Field
from typing import Optional, Literal

class RpeComputeRequest(BaseModel):
    """Request to compute set params from RPE and user max.
    Provide any two of: intensity (1-100), effort (1-10), volume (reps >=1).
    Optionally provide user_max_id or max_weight directly to compute working weight.
    """
    intensity: Optional[int] = Field(default=None, ge=1, le=100)
    effort: Optional[float] = Field(default=None, ge=1, le=10)
    volume: Optional[int] = Field(default=None, ge=1)

    user_max_id: Optional[int] = None
    max_weight: Optional[float] = Field(default=None, ge=0)

    rounding_step: float = Field(default=2.5, gt=0)
    rounding_mode: Literal['nearest', 'floor', 'ceil'] = Field(default='nearest')

class RpeComputeResponse(BaseModel):
    intensity: Optional[int] = None
    effort: Optional[float] = None
    volume: Optional[int] = None
    weight: Optional[float] = None
