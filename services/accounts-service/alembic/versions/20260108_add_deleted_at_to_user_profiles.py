"""accounts: add deleted_at to user_profiles

Revision ID: 20260108_add_deleted_at
Revises: 20251208_add_stripe_connect
Create Date: 2026-01-08
"""

import sqlalchemy as sa
from alembic import op

revision = "20260108_add_deleted_at"
down_revision = "20251208_add_stripe_connect"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c.get("name") for c in insp.get_columns("user_profiles")}

    if "deleted_at" not in cols:
        op.add_column("user_profiles", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    index_names = {idx.get("name") for idx in insp.get_indexes("user_profiles")}
    if "ix_user_profiles_deleted_at" not in index_names:
        op.create_index("ix_user_profiles_deleted_at", "user_profiles", ["deleted_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    index_names = {idx.get("name") for idx in insp.get_indexes("user_profiles")}
    if "ix_user_profiles_deleted_at" in index_names:
        op.drop_index("ix_user_profiles_deleted_at", table_name="user_profiles")

    cols = {c.get("name") for c in insp.get_columns("user_profiles")}
    if "deleted_at" in cols:
        op.drop_column("user_profiles", "deleted_at")
