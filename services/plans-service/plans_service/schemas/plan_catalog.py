"""Additive catalog contract; stored goal and level codes are preserved verbatim."""
from pydantic import BaseModel


class CatalogItem(BaseModel):
    id: int
    name: str
    duration_weeks: int
    primary_goal: str | None = None
    intended_experience_level: str | None = None
    intended_frequency_per_week: int | None = None
    session_duration_target_min: int | None = None


class FacetValue(BaseModel):
    value: str | int
    count: int


class CatalogResponse(BaseModel):
    items: list[CatalogItem]
    total: int
    offset: int
    limit: int
    facets: dict[str, list[FacetValue]]
