"""initial user_maxes table

Revision ID: 0001_initial_user_maxes
Revises: 
Create Date: 2025-08-27 12:08:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_initial_user_maxes"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_maxes",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("exercise_id", sa.Integer, nullable=False),
        sa.Column("max_weight", sa.Integer, nullable=False),
        sa.Column("rep_max", sa.Integer, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("user_maxes")
