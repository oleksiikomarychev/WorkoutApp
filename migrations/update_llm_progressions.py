from alembic import op
import sqlalchemy as sa


def upgrade():
    # Make intensity and effort columns nullable
    with op.batch_alter_table('llm_progressions', schema=None) as batch_op:
        batch_op.alter_column('intensity',
                           existing_type=sa.INTEGER(),
                           nullable=True)
        batch_op.alter_column('effort',
                           existing_type=sa.INTEGER(),
                           nullable=True)
        batch_op.alter_column('volume',
                           existing_type=sa.INTEGER(),
                           nullable=True)


def downgrade():
    # Revert the changes if needed
    with op.batch_alter_table('llm_progressions', schema=None) as batch_op:
        batch_op.alter_column('intensity',
                           existing_type=sa.INTEGER(),
                           nullable=False)
        batch_op.alter_column('effort',
                           existing_type=sa.INTEGER(),
                           nullable=False)
        batch_op.alter_column('volume',
                           existing_type=sa.INTEGER(),
                           nullable=False)
