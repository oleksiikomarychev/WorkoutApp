"""Remove llm_recommendation column from llm_progressions table"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    # Remove the llm_recommendation column
    with op.batch_alter_table('llm_progressions', schema=None) as batch_op:
        batch_op.drop_column('llm_recommendation')


def downgrade():
    # Add the column back if needed (with the same definition as before)
    with op.batch_alter_table('llm_progressions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('llm_recommendation', sa.TEXT(), nullable=True))
