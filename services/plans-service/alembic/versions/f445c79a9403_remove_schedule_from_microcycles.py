"""remove schedule from microcycles

Revision ID: f445c79a9403
Revises: db821c13a941
Create Date: 2025-09-20 02:10:59.510788
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f445c79a9403"
down_revision = "db821c13a941"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("microcycles", "schedule")


def downgrade():
    op.add_column(
        "microcycles",
        sa.Column("schedule", postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=False),
    )
