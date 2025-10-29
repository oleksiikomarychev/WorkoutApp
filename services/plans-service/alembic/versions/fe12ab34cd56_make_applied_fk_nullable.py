"""make_applied_fk_nullable

Revision ID: fe12ab34cd56
Revises: 7bbaddb6e0d7
Create Date: 2025-10-29 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fe12ab34cd56'
down_revision = 'c1f2a3b4d5e6'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # applied_mesocycles.mesocycle_id -> nullable
    with op.batch_alter_table('applied_mesocycles') as batch_op:
        batch_op.alter_column('mesocycle_id', existing_type=sa.Integer(), nullable=True)
    # applied_microcycles.microcycle_id -> nullable
    with op.batch_alter_table('applied_microcycles') as batch_op:
        batch_op.alter_column('microcycle_id', existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    # Revert to NOT NULL
    with op.batch_alter_table('applied_mesocycles') as batch_op:
        batch_op.alter_column('mesocycle_id', existing_type=sa.Integer(), nullable=False)
    with op.batch_alter_table('applied_microcycles') as batch_op:
        batch_op.alter_column('microcycle_id', existing_type=sa.Integer(), nullable=False)
