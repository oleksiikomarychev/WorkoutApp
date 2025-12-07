"""add exercise_instances indexes

Revision ID: c1d2e3f4g5h6
Revises: b1d2c3d4e5f6
Create Date: 2025-10-12 22:30:00.000000
"""

from alembic import op

revision = "c1d2e3f4g5h6"
down_revision = "b1d2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_exercise_instances_user_id",
        "exercise_instances",
        ["user_id"],
        unique=False,
    )

    op.create_index(
        "ix_exercise_instances_user_workout",
        "exercise_instances",
        ["user_id", "workout_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_exercise_instances_user_workout", table_name="exercise_instances")
    op.drop_index("ix_exercise_instances_user_id", table_name="exercise_instances")
