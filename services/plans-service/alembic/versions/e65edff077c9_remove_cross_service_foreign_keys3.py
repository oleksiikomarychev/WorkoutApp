"""Remove cross-service foreign keys3

Revision ID: e65edff077c9
Revises: 4630a657ee87
Create Date: 2025-09-19 00:47:54.537520
"""

import sqlalchemy as sa
from alembic import op

revision = "e65edff077c9"
down_revision = "4630a657ee87"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("calendar_plans", "is_active", existing_type=sa.BOOLEAN(), nullable=True)


def downgrade():
    op.alter_column("calendar_plans", "is_active", existing_type=sa.BOOLEAN(), nullable=False)
