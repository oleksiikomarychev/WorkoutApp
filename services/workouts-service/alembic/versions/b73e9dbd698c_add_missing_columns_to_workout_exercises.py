"""add missing columns to workout_exercises"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b73e9dbd698c'
down_revision = '3f98d65839be'
branch_labels = None
depends_on = None


def upgrade():
    # Add missing columns to workout_exercises
    op.add_column('workout_exercises', sa.Column('order', sa.Integer(), nullable=True))
    op.add_column('workout_exercises', sa.Column('notes', sa.String(), nullable=True))
    op.add_column('workout_exercises', sa.Column('rest_seconds', sa.Integer(), nullable=True))


def downgrade():
    # Remove the columns
    op.drop_column('workout_exercises', 'rest_seconds')
    op.drop_column('workout_exercises', 'notes')
    op.drop_column('workout_exercises', 'order')
