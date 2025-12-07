"""Add indexes for plan hierarchy foreign keys

Revision ID: 9abcde123456
Revises: f015b8b5c1f1
Create Date: 2025-12-05 01:50:00.000000
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "9abcde123456"
down_revision: str | None = "f015b8b5c1f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add non-unique indexes on FK columns used in plan hierarchy selects.

    These indexes speed up the selectinload chains over:
    - CalendarPlan -> Mesocycle -> Microcycle -> PlanWorkout -> PlanExercise -> PlanSet
    - AppliedCalendarPlan -> AppliedMesocycle -> AppliedMicrocycle -> AppliedWorkout
    """

    op.create_index(
        "ix_mesocycles_calendar_plan_id",
        "mesocycles",
        ["calendar_plan_id"],
        unique=False,
    )
    op.create_index(
        "ix_microcycles_mesocycle_id",
        "microcycles",
        ["mesocycle_id"],
        unique=False,
    )
    op.create_index(
        "ix_plan_workouts_microcycle_id",
        "plan_workouts",
        ["microcycle_id"],
        unique=False,
    )
    op.create_index(
        "ix_plan_exercises_plan_workout_id",
        "plan_exercises",
        ["plan_workout_id"],
        unique=False,
    )
    op.create_index(
        "ix_plan_sets_plan_exercise_id",
        "plan_sets",
        ["plan_exercise_id"],
        unique=False,
    )

    op.create_index(
        "ix_applied_mesocycles_applied_plan_id",
        "applied_mesocycles",
        ["applied_plan_id"],
        unique=False,
    )
    op.create_index(
        "ix_applied_microcycles_applied_mesocycle_id",
        "applied_microcycles",
        ["applied_mesocycle_id"],
        unique=False,
    )
    op.create_index(
        "ix_applied_microcycles_microcycle_id",
        "applied_microcycles",
        ["microcycle_id"],
        unique=False,
    )
    op.create_index(
        "ix_applied_workouts_applied_microcycle_id",
        "applied_workouts",
        ["applied_microcycle_id"],
        unique=False,
    )
    op.create_index(
        "ix_applied_calendar_plans_calendar_plan_id",
        "applied_calendar_plans",
        ["calendar_plan_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop FK helper indexes for plan hierarchy."""

    op.drop_index(
        "ix_applied_calendar_plans_calendar_plan_id",
        table_name="applied_calendar_plans",
    )
    op.drop_index(
        "ix_applied_workouts_applied_microcycle_id",
        table_name="applied_workouts",
    )
    op.drop_index(
        "ix_applied_microcycles_microcycle_id",
        table_name="applied_microcycles",
    )
    op.drop_index(
        "ix_applied_microcycles_applied_mesocycle_id",
        table_name="applied_microcycles",
    )
    op.drop_index(
        "ix_applied_mesocycles_applied_plan_id",
        table_name="applied_mesocycles",
    )

    op.drop_index(
        "ix_plan_sets_plan_exercise_id",
        table_name="plan_sets",
    )
    op.drop_index(
        "ix_plan_exercises_plan_workout_id",
        table_name="plan_exercises",
    )
    op.drop_index(
        "ix_plan_workouts_microcycle_id",
        table_name="plan_workouts",
    )
    op.drop_index(
        "ix_microcycles_mesocycle_id",
        table_name="microcycles",
    )
    op.drop_index(
        "ix_mesocycles_calendar_plan_id",
        table_name="mesocycles",
    )
