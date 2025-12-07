"""Add plan_workout_id to workouts

Revision ID: 987654321def
Revises: e6525343955a
Create Date: 2025-09-16 20:50:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "987654321def"
down_revision = "e6525343955a"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("workouts", sa.Column("plan_workout_id", sa.Integer(), nullable=True))
    op.add_column("workouts", sa.Column("is_template", sa.Boolean(), default=False))
    op.create_index("ix_workouts_plan_workout_id", "workouts", ["plan_workout_id"])


def downgrade():
    op.drop_index("ix_workouts_plan_workout_id", "workouts")
    op.drop_column("workouts", "is_template")
    op.drop_column("workouts", "plan_workout_id")
