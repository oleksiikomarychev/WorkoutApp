"""drop movement_pattern from exercise_list

Revision ID: d4f1a8c2b9e0
Revises: c3a9f4b0d1e2
Create Date: 2025-12-13 23:20:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "d4f1a8c2b9e0"
down_revision = "c3a9f4b0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("exercise_list", schema=None) as batch_op:
        batch_op.drop_column("movement_pattern")


def downgrade() -> None:
    with op.batch_alter_table("exercise_list", schema=None) as batch_op:
        batch_op.add_column(sa.Column("movement_pattern", sa.String(length=64), nullable=True))
