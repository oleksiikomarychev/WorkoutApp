from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PlanAnalyticsItem(BaseModel):
    workout_id: int
    order_index: int | None = None
    date: datetime | None = None
    metrics: dict[str, float]
    actual_metrics: dict[str, float] | None = None


class PlanAnalyticsResponse(BaseModel):
    items: list[PlanAnalyticsItem]
