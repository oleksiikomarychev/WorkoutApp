"""Helpers for persisting generated plans."""

from __future__ import annotations

from sqlalchemy.orm import Session

from .. import models


def save_generated_plan(db: Session, plan, user_id: str):
    """Persist a generated training plan to the agent-service database."""
    db_plan = models.GeneratedPlan(
        user_id=user_id,
        plan_data=plan.model_dump(),
    )
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    return db_plan
