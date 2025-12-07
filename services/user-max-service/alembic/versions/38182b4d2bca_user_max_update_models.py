"""user-max: update models

Revision ID: 38182b4d2bca
Revises: merge_f1g2_e011d
Create Date: 2025-11-15 22:10:10.679758
"""

import sqlalchemy as sa
from alembic import op

revision = "38182b4d2bca"
down_revision = "merge_f1g2_e011d"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    op.create_table(
        "user_maxes",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.VARCHAR(length=255), autoincrement=False, nullable=False),
        sa.Column("exercise_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column("max_weight", sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False),
        sa.Column("date", sa.DATE(), autoincrement=False, nullable=False),
        sa.Column(
            "rep_max",
            sa.INTEGER(),
            server_default=sa.text("0"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column("true_1rm", sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
        sa.Column("verified_1rm", sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
        sa.Column("exercise_name", sa.VARCHAR(length=255), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint("id", name="user_maxes_pkey"),
    )
    op.create_index("ix_user_maxes_user_id", "user_maxes", ["user_id"], unique=False)
    op.create_index(
        "ix_user_maxes_unique_entry",
        "user_maxes",
        ["user_id", "exercise_id", "rep_max", "date"],
        unique=True,
    )
