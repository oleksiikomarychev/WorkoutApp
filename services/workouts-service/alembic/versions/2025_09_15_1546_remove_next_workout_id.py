"""Remove next_workout_id from workouts table

Revision ID: 2025_09_15_1546
Revises: 2025_09_15_1217
Create Date: 2025-09-15 15:46:20.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "2025_09_15_1546"
down_revision = "2025_09_15_1217"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("workouts", "next_workout_id")


def downgrade():
    op.add_column(
        "workouts",
        sa.Column("next_workout_id", sa.Integer(), sa.ForeignKey("workouts.id"), nullable=True),
    )
