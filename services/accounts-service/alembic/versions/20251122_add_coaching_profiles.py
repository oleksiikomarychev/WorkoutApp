"""add coaching profile table

Revision ID: 20251122_add_coaching_profiles
Revises: 20251116_init_accounts_models
Create Date: 2025-11-22 12:15:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20251122_add_coaching_profiles"
down_revision = "20251116_init_accounts_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_coaching_profiles",
        sa.Column("user_id", sa.String(), sa.ForeignKey("user_profiles.user_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("accepting_clients", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("tagline", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "specializations",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "languages", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column("experience_years", sa.Integer(), nullable=True),
        sa.Column("timezone", sa.String(), nullable=True),
        sa.Column("rate_type", sa.String(length=32), nullable=True),
        sa.Column("rate_currency", sa.String(length=3), nullable=True),
        sa.Column("rate_amount_minor", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("user_coaching_profiles")
