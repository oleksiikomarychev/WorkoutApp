from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel


class PlanAnalyticsItem(BaseModel):
    workout_id: int
    order_index: Optional[int] = None
    date: Optional[datetime] = None
    metrics: Dict[str, float]


class PlanAnalyticsResponse(BaseModel):
    items: list[PlanAnalyticsItem]
