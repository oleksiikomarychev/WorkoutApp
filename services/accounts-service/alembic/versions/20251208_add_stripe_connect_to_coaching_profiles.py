"""add stripe connect account field to coaching profiles

Revision ID: 20251208_add_stripe_connect
Revises: 8b57bf954ef7
Create Date: 2025-12-08
"""

import sqlalchemy as sa
from alembic import op

revision = "20251208_add_stripe_connect"
down_revision = "20251123_restore_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_coaching_profiles",
        sa.Column("stripe_connect_account_id", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "ix_user_coaching_profiles_stripe_connect_account_id",
        "user_coaching_profiles",
        ["stripe_connect_account_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_user_coaching_profiles_stripe_connect_account_id",
        table_name="user_coaching_profiles",
    )
    op.drop_column("user_coaching_profiles", "stripe_connect_account_id")
