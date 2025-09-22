"""Create ParamsWorkout table and update Microcycle"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '1234abcd5678'
down_revision = '7bbaddb6e0d7'
branch_labels = None
depends_on = None


def upgrade():
    # Create params_workouts table
    op.create_table('params_workouts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('parameters', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )
    
    # Drop schedule column from microcycles
    op.drop_column('microcycles', 'schedule')
    
    # Add params_workout_ids column to microcycles
    op.add_column('microcycles',
        sa.Column('params_workout_ids', postgresql.ARRAY(sa.Integer()), nullable=True)
    )


def downgrade():
    # Remove params_workout_ids column
    op.drop_column('microcycles', 'params_workout_ids')
    
    # Recreate schedule column
    op.add_column('microcycles',
        sa.Column('schedule', postgresql.JSONB(), nullable=True)
    )
    
    # Drop params_workouts table
    op.drop_table('params_workouts')
