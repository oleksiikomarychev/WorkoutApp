"""add rest_seconds to exercise_instances

Revision ID: 2026_01_09_rest_seconds
Revises: ab12cd34ef56
Create Date: 2026-01-09
"""

import sqlalchemy as sa
from alembic import op

revision = "2026_01_09_rest_seconds"
down_revision = "ab12cd34ef56"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("exercise_instances", schema=None) as batch_op:
        batch_op.add_column(sa.Column("rest_seconds", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("exercise_instances", schema=None) as batch_op:
        batch_op.drop_column("rest_seconds")
