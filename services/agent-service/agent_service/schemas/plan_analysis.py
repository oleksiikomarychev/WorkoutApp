from typing import Any

from pydantic import BaseModel, Field


class PlanAnalysisRequest(BaseModel):
    applied_plan_id: int = Field(..., ge=1, description="ID of the applied plan to analyze")


class PlanAnalysisResponse(BaseModel):
    summary: str = Field(..., description="Markdown formatted analysis and recommendations")
    metrics: dict[str, Any] = Field(default_factory=dict, description="Key metrics used for analysis")
