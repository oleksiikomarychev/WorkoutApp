"""add category/movement_pattern/is_competition_lift to exercise_list

Revision ID: e1f2a3b4c5d6
Revises: c1d2e3f4g5h6
Create Date: 2025-12-07 15:49:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "e1f2a3b4c5d6"
down_revision = "c1d2e3f4g5h6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("exercise_list", schema=None) as batch_op:
        batch_op.add_column(sa.Column("category", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("movement_pattern", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("is_competition_lift", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("exercise_list", schema=None) as batch_op:
        batch_op.drop_column("is_competition_lift")
        batch_op.drop_column("movement_pattern")
        batch_op.drop_column("category")
