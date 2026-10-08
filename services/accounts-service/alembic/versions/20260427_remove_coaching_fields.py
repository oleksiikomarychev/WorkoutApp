"""remove accepting_clients, rate_type, rate_currency from coaching profiles

Revision ID: 20260427_remove_coaching_fields
Revises: 20260127_add_rating_fields
Create Date: 2026-04-27
"""

import sqlalchemy as sa
from alembic import op

revision = "20260427_remove_coaching_fields"
down_revision = "20260127_add_rating_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c.get("name") for c in insp.get_columns("user_coaching_profiles")}

    if "accepting_clients" in cols:
        op.drop_column("user_coaching_profiles", "accepting_clients")
    if "rate_type" in cols:
        op.drop_column("user_coaching_profiles", "rate_type")
    if "rate_currency" in cols:
        op.drop_column("user_coaching_profiles", "rate_currency")


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c.get("name") for c in insp.get_columns("user_coaching_profiles")}

    if "accepting_clients" not in cols:
        op.add_column(
            "user_coaching_profiles",
            sa.Column("accepting_clients", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )
    if "rate_type" not in cols:
        op.add_column(
            "user_coaching_profiles",
            sa.Column("rate_type", sa.String(length=32), nullable=True),
        )
    if "rate_currency" not in cols:
        op.add_column(
            "user_coaching_profiles",
            sa.Column("rate_currency", sa.String(length=3), nullable=True),
        )
