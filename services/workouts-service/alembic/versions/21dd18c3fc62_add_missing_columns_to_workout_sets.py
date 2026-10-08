"""add missing columns to workout_sets"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '21dd18c3fc62'
down_revision = 'b73e9dbd698c'
branch_labels = None
depends_on = None


def upgrade():
    # Add missing columns to workout_sets
    op.add_column('workout_sets', sa.Column('order_index', sa.Integer(), nullable=True))
    op.add_column('workout_sets', sa.Column('subsets', postgresql.JSON(astext_type=sa.Text()), nullable=True))


def downgrade():
    # Remove the columns
    op.drop_column('workout_sets', 'subsets')
    op.drop_column('workout_sets', 'order_index')
