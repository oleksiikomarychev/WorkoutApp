"""Add missing columns to plan_exercises table

Revision ID: add_missing_cols_plan_exercises
Revises: 7bbaddb6e0d7
Create Date: 2025-09-20 18:48:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_missing_cols_plan_exercises'
down_revision = '21993251eec4'
branch_labels = None
depends_on = None


def upgrade():
    # Check existing columns and only add missing ones
    conn = op.get_bind()
    
    # Get existing columns in plan_exercises table
    result = conn.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_name = 'plan_exercises' AND table_schema = 'public'"))
    existing_columns = [row[0] for row in result.fetchall()]
    
    # Add missing columns conditionally
    if 'exercise_definition_id' not in existing_columns:
        op.add_column('plan_exercises',
            sa.Column('exercise_definition_id', sa.Integer(), nullable=True)
        )
    
    if 'exercise_name' not in existing_columns:
        op.add_column('plan_exercises', 
            sa.Column('exercise_name', sa.String(length=255), nullable=True)
        )
    
    if 'order_index' not in existing_columns:
        op.add_column('plan_exercises',
            sa.Column('order_index', sa.Integer(), nullable=False, server_default='0')
        )
    
    if 'created_at' not in existing_columns:
        op.add_column('plan_exercises',
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
        )
    
    if 'updated_at' not in existing_columns:
        op.add_column('plan_exercises',
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
        )
    
    # Update existing rows with default values for newly added columns
    if 'exercise_definition_id' not in existing_columns:
        op.execute("UPDATE plan_exercises SET exercise_definition_id = 1 WHERE exercise_definition_id IS NULL")
        op.alter_column('plan_exercises', 'exercise_definition_id', nullable=False)
    
    if 'exercise_name' not in existing_columns:
        op.execute("UPDATE plan_exercises SET exercise_name = 'Unknown Exercise' WHERE exercise_name IS NULL")
        op.alter_column('plan_exercises', 'exercise_name', nullable=False)


def downgrade():
    # Remove the added columns
    op.drop_column('plan_exercises', 'exercise_definition_id')
    op.drop_column('plan_exercises', 'exercise_name')
    op.drop_column('plan_exercises', 'order_index')
    op.drop_column('plan_exercises', 'created_at')
    op.drop_column('plan_exercises', 'updated_at')
