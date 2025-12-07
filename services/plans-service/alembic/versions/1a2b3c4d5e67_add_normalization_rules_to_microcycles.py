"""add normalization_rules to microcycles

Revision ID: 1a2b3c4d5e67
Revises: f990c648024b
Create Date: 2025-11-19 20:50:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "1a2b3c4d5e67"
down_revision = "f990c648024b"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "microcycles",
        sa.Column("normalization_rules", sa.JSON(), nullable=True),
    )


def downgrade():
    op.drop_column("microcycles", "normalization_rules")
