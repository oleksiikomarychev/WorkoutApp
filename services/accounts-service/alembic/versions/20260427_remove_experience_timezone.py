"""remove experience_years and timezone from coaching profiles

Revision ID: 20260427_rm_exp_tz
Revises: 20260427_remove_coaching_fields
Create Date: 2026-04-27
"""

import sqlalchemy as sa
from alembic import op

revision = "20260427_rm_exp_tz"
down_revision = "20260427_remove_coaching_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c.get("name") for c in insp.get_columns("user_coaching_profiles")}

    if "experience_years" in cols:
        op.drop_column("user_coaching_profiles", "experience_years")
    if "timezone" in cols:
        op.drop_column("user_coaching_profiles", "timezone")


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c.get("name") for c in insp.get_columns("user_coaching_profiles")}

    if "experience_years" not in cols:
        op.add_column(
            "user_coaching_profiles",
            sa.Column("experience_years", sa.Integer(), nullable=True),
        )
    if "timezone" not in cols:
        op.add_column(
            "user_coaching_profiles",
            sa.Column("timezone", sa.String(), nullable=True),
        )
