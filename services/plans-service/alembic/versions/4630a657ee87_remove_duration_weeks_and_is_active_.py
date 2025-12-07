"""Remove duration_weeks and is_active columns

Revision ID: 4630a657ee87
Revises: d0afaef60b26
Create Date: 2025-09-19 00:41:55.349441
"""

import sqlalchemy as sa
from alembic import op

revision = "4630a657ee87"
down_revision = "d0afaef60b26"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(op.f("ix_applied_plan_workouts_id"), "applied_plan_workouts", ["id"], unique=False)
    op.create_index(op.f("ix_applied_workouts_id"), "applied_workouts", ["id"], unique=False)

    op.add_column("calendar_plans", sa.Column("duration_weeks", sa.Integer(), nullable=True))

    op.execute("UPDATE calendar_plans SET duration_weeks = 1")

    op.alter_column("calendar_plans", "duration_weeks", nullable=False)

    op.add_column("calendar_plans", sa.Column("is_active", sa.Boolean(), nullable=True))
    op.execute("UPDATE calendar_plans SET is_active = true")
    op.alter_column("calendar_plans", "is_active", nullable=False)

    op.add_column("mesocycles", sa.Column("duration_weeks", sa.Integer(), nullable=True))
    op.execute("UPDATE mesocycles SET duration_weeks = 1")
    op.alter_column("mesocycles", "duration_weeks", nullable=False)


def downgrade():
    op.drop_column("mesocycles", "duration_weeks")
    op.drop_column("calendar_plans", "is_active")
    op.drop_column("calendar_plans", "duration_weeks")
    op.drop_index(op.f("ix_applied_workouts_id"), table_name="applied_workouts")
    op.drop_index(op.f("ix_applied_plan_workouts_id"), table_name="applied_plan_workouts")
