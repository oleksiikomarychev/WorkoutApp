from typing import Any, Dict

from pydantic import BaseModel, Field


class PlanAnalysisRequest(BaseModel):
    """Request to analyze an applied plan."""

    applied_plan_id: int = Field(..., ge=1, description="ID of the applied plan to analyze")


class PlanAnalysisResponse(BaseModel):
    """Response containing the analysis and recommendations."""

    summary: str = Field(..., description="Markdown formatted analysis and recommendations")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Key metrics used for analysis")
