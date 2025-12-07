"""Add unique constraint to prevent duplicate workouts

Revision ID: 2025_10_13_unique_workout
Revises: 2025_10_12_add_user_id
Create Date: 2025-10-13 01:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "2025_10_13_unique_workout"
down_revision = "60d14a510cba"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_workouts_unique_plan_order",
        "workouts",
        ["user_id", "applied_plan_id", "plan_order_index"],
        unique=True,
        postgresql_where=sa.text("applied_plan_id IS NOT NULL AND plan_order_index IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_workouts_unique_plan_order", table_name="workouts")
