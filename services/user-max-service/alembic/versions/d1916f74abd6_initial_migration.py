"""Initial migration

Revision ID: d1916f74abd6
Revises:
Create Date: 2025-09-05 16:44:44.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d1916f74abd6"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_maxes",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("exercise_id", sa.Integer, nullable=False),
        sa.Column("max_weight", sa.Integer, nullable=False),
        sa.Column("rep_max", sa.Integer, nullable=False),
        sa.Column("date", sa.Date, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("user_maxes")
