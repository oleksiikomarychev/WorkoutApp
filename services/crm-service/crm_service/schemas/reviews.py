from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CoachReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5 stars")
    comment: str | None = Field(None, max_length=5000, description="Optional review comment")


class CoachReviewResponse(BaseModel):
    id: int
    link_id: int
    reviewer_id: str
    reviewer_name: str | None = None
    coach_id: str
    rating: int
    comment: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CoachReviewListResponse(BaseModel):
    reviews: list[CoachReviewResponse]
    total: int
    limit: int
    offset: int
