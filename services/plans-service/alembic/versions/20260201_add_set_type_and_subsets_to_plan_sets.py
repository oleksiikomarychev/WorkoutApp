"""Add set_type and subsets to plan_sets

Revision ID: 20260201_add_set_type_and_subsets_to_plan_sets
Revises: d3a9c4b7e1f2
Create Date: 2026-02-01
"""

import sqlalchemy as sa
from alembic import op

revision = "20260201_add_set_type_and_subsets_to_plan_sets"
down_revision = "d3a9c4b7e1f2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("plan_sets", sa.Column("set_type", sa.String(length=32), nullable=True))
    op.add_column("plan_sets", sa.Column("subsets", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("plan_sets", "subsets")
    op.drop_column("plan_sets", "set_type")
