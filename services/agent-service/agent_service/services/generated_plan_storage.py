"""Storage service for generated plans in agent-service."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models


def save_generated_plan(db: Session, plan: BaseModel | Any, user_id: str) -> models.GeneratedPlan:
    """Persist a generated training plan into the database."""
    plan_data = plan.model_dump(mode="json") if isinstance(plan, BaseModel) else plan
    db_plan = models.GeneratedPlan(
        user_id=user_id,
        plan_data=plan_data,
    )
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    return db_plan
