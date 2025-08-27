"""add workout_sessions table

Revision ID: 0002_workout_sessions
Revises: 0001_initial_workouts
Create Date: 2025-08-27 12:45:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002_workout_sessions"
down_revision: Union[str, None] = "0001_initial_workouts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workout_sessions",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("workout_id", sa.Integer, nullable=False, index=True),
        sa.Column("started_at", sa.DateTime, nullable=False),
        sa.Column("finished_at", sa.DateTime, nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
    )


def downgrade() -> None:
    op.drop_table("workout_sessions")
