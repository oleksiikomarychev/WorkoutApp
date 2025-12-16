"""drop category from exercise_list

Revision ID: c3a9f4b0d1e2
Revises: 9c4e7a2b1d0f
Create Date: 2025-12-13 23:05:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "c3a9f4b0d1e2"
down_revision = "9c4e7a2b1d0f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("exercise_list", schema=None) as batch_op:
        batch_op.drop_column("category")


def downgrade() -> None:
    with op.batch_alter_table("exercise_list", schema=None) as batch_op:
        batch_op.add_column(sa.Column("category", sa.String(length=64), nullable=True))
