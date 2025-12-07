"""add missing columns to user_maxes

Revision ID: add_missing_columns
Revises: d1916f74abd6
Create Date: 2025-09-10 18:35:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "add_missing_columns"
down_revision = "d1916f74abd6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("user_maxes", "user_id", nullable=True)

    op.add_column("user_maxes", sa.Column("true_1rm", sa.Float(), nullable=True))
    op.add_column("user_maxes", sa.Column("verified_1rm", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("user_maxes", "verified_1rm")
    op.drop_column("user_maxes", "true_1rm")

    op.alter_column("user_maxes", "user_id", nullable=False)
