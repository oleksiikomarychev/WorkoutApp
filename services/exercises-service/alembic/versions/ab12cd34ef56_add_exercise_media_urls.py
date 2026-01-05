"""add image_url and gif_url to exercise_list

Revision ID: ab12cd34ef56
Revises: d4f1a8c2b9e0
Create Date: 2026-01-04
"""

import sqlalchemy as sa
from alembic import op

revision = "ab12cd34ef56"
down_revision = "d4f1a8c2b9e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("exercise_list", schema=None) as batch_op:
        batch_op.add_column(sa.Column("image_url", sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column("gif_url", sa.String(length=512), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("exercise_list", schema=None) as batch_op:
        batch_op.drop_column("gif_url")
        batch_op.drop_column("image_url")
