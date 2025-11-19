"""Add macro_suggestion JSON column to workout_sessions

Revision ID: 2025_10_28_macro_suggestion
Revises: 2025_10_13_unique_workout
Create Date: 2025-10-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2025_10_28_macro_suggestion'
down_revision = '2025_10_13_unique_workout'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('workout_sessions', sa.Column('macro_suggestion', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('workout_sessions', 'macro_suggestion')
