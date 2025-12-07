"""user-max: daily aggregates table

Revision ID: 8a4f6dba3c01
Revises: 77e251465fb5
Create Date: 2025-12-05 00:00:00.000000
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "8a4f6dba3c01"
down_revision: str | None = "77e251465fb5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_max_daily_agg",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("exercise_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("sum_true_1rm", sa.Float(), nullable=False),
        sa.Column("cnt", sa.Integer(), nullable=False),
    )
    op.create_index(
        "ix_user_max_daily_agg_user_ex",
        "user_max_daily_agg",
        ["user_id", "exercise_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_max_daily_agg_user_ex_date",
        "user_max_daily_agg",
        ["user_id", "exercise_id", "date"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_user_max_daily_agg_user_ex_date", table_name="user_max_daily_agg")
    op.drop_index("ix_user_max_daily_agg_user_ex", table_name="user_max_daily_agg")
    op.drop_table("user_max_daily_agg")
