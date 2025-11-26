"""Add next_workout_id to workouts table

Revision ID: 2025_09_15_1217
Revises: <previous_revision_id>
Create Date: 2025-09-15 12:17:49.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "2025_09_15_1217"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "workouts",
        sa.Column("next_workout_id", sa.Integer(), sa.ForeignKey("workouts.id"), nullable=True),
    )


def downgrade():
    op.drop_column("workouts", "next_workout_id")
