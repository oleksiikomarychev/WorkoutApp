"""Add microcycle_id to workouts

Revision ID: 3d4b6a8f0c1a
Revises: 2c3b5d7e9f01
Create Date: 2025-09-18 13:21:07.123456

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3d4b6a8f0c1a'
down_revision = '987654321def'
branch_labels = None
depends_on = None


def upgrade():
    # Added microcycle_id without foreign key constraint since microcycles table is in another service
    op.add_column('workouts', sa.Column('microcycle_id', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('workouts', 'microcycle_id')
