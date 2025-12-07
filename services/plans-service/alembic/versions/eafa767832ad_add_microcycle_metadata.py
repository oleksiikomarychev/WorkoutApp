"""add microcycle metadata

Revision ID: eafa767832ad
Revises: fix_exercise_columns_mismatch
Create Date: 2025-10-02 20:03:20.038857
"""

import sqlalchemy as sa
from alembic import op

revision = "eafa767832ad"
down_revision = "fix_exercise_columns_mismatch"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("workout_progress", "user_id")


def downgrade():
    op.add_column(
        "workout_progress",
        sa.Column("user_id", sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    )
