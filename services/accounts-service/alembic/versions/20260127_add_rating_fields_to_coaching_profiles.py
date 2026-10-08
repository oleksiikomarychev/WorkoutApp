"""add rating fields to coaching profiles

Revision ID: 20260127_add_rating_fields
Revises: 20260108_add_deleted_at
Create Date: 2026-01-27
"""

import sqlalchemy as sa
from alembic import op

revision = "20260127_add_rating_fields"
down_revision = "20260108_add_deleted_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_coaching_profiles",
        sa.Column("average_rating", sa.Float(), nullable=True),
    )
    op.add_column(
        "user_coaching_profiles",
        sa.Column("review_count", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("user_coaching_profiles", "review_count")
    op.drop_column("user_coaching_profiles", "average_rating")
