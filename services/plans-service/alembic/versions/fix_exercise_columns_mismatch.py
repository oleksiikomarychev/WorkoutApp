"""Fix column mismatch in plan_exercises table

Revision ID: fix_exercise_columns_mismatch
Revises: add_missing_cols_plan_exercises
Create Date: 2025-09-20 18:55:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fix_exercise_columns_mismatch'
down_revision = 'add_missing_cols_plan_exercises'
branch_labels = None
depends_on = None


def upgrade():
    # Check if exercise_id column exists and drop it if it shouldn't be there
    conn = op.get_bind()
    
    # Get existing columns in plan_exercises table
    result = conn.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_name = 'plan_exercises' AND table_schema = 'public'"))
    existing_columns = [row[0] for row in result.fetchall()]
    
    # If exercise_id exists but we don't want it, drop it
    if 'exercise_id' in existing_columns and 'exercise_definition_id' in existing_columns:
        # First, make exercise_id nullable so we can drop it
        op.alter_column('plan_exercises', 'exercise_id', nullable=True)
        
        # Set any null values to a default
        op.execute("UPDATE plan_exercises SET exercise_id = 1 WHERE exercise_id IS NULL")
        
        # Drop the exercise_id column since we only want exercise_definition_id
        op.drop_column('plan_exercises', 'exercise_id')


def downgrade():
    # Re-add exercise_id column if needed
    op.add_column('plan_exercises', sa.Column('exercise_id', sa.Integer(), nullable=True))
