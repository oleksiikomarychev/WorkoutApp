"""add coach reviews table

Revision ID: 20260127_add_coach_reviews
Revises: 20251208_add_payments
Create Date: 2026-01-27
"""

import sqlalchemy as sa
from alembic import op

revision = "20260127_add_coach_reviews"
down_revision = "20251208_add_payments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "coach_reviews",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("link_id", sa.Integer, sa.ForeignKey("coach_athlete_links.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("reviewer_id", sa.String(length=255), nullable=False, index=True),
        sa.Column("coach_id", sa.String(length=255), nullable=False, index=True),
        sa.Column("rating", sa.Integer, nullable=False),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("link_id", "reviewer_id", name="uq_link_reviewer"),
    )
    op.create_index(
        "ix_coach_reviews_coach_created",
        "coach_reviews",
        ["coach_id", "created_at"],
    )
    op.create_index(
        "ix_coach_reviews_link_reviewer",
        "coach_reviews",
        ["link_id", "reviewer_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_coach_reviews_link_reviewer", table_name="coach_reviews")
    op.drop_index("ix_coach_reviews_coach_created", table_name="coach_reviews")
    op.drop_table("coach_reviews")
