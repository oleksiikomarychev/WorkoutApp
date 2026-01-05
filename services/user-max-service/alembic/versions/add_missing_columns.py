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
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("user_maxes", schema=None) as batch_op:
            batch_op.alter_column("user_id", nullable=True)
            batch_op.add_column(sa.Column("true_1rm", sa.Float(), nullable=True))
            batch_op.add_column(sa.Column("verified_1rm", sa.Float(), nullable=True))
    else:
        op.alter_column("user_maxes", "user_id", nullable=True)
        op.add_column("user_maxes", sa.Column("true_1rm", sa.Float(), nullable=True))
        op.add_column("user_maxes", sa.Column("verified_1rm", sa.Float(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("user_maxes", schema=None) as batch_op:
            batch_op.drop_column("verified_1rm")
            batch_op.drop_column("true_1rm")
            batch_op.alter_column("user_id", nullable=False)
    else:
        op.drop_column("user_maxes", "verified_1rm")
        op.drop_column("user_maxes", "true_1rm")
        op.alter_column("user_maxes", "user_id", nullable=False)
