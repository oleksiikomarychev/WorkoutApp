from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime

class PlanAnalyticsItem(BaseModel):
    workout_id: int
    order_index: Optional[int] = None
    date: Optional[datetime] = None
    metrics: Dict[str, float]

class PlanAnalyticsResponse(BaseModel):
    items: list[PlanAnalyticsItem]
