"""Rename ended_at to finished_at in workout_sessions

Revision ID: 2025_10_08_rename
Revises: b7ec1abde58b
Create Date: 2025-10-08 03:35:00

"""

from alembic import op

revision = "2025_10_08_rename"
down_revision = "b7ec1abde58b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("workout_sessions", "ended_at", new_column_name="finished_at")


def downgrade() -> None:
    op.alter_column("workout_sessions", "finished_at", new_column_name="ended_at")
