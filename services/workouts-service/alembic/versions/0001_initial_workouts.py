"""initial workouts table

Revision ID: 0001_initial_workouts
Revises: 
Create Date: 2025-08-27 12:20:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_initial_workouts"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workouts",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("applied_plan_id", sa.Integer, nullable=True),
        sa.Column("plan_order_index", sa.Integer, nullable=True),
        sa.Column("scheduled_for", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("notes", sa.String, nullable=True),
        sa.Column("status", sa.String(length=64), nullable=True),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("duration_seconds", sa.Integer, nullable=True),
        sa.Column("rpe_session", sa.Float, nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("readiness_score", sa.Integer, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("workouts")
