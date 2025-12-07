"""add_exercise_name_to_user_max

Revision ID: e011d561b6c7
Revises: 7ded9e261229
Create Date: 2025-09-17 13:10:53.957298
"""

import sqlalchemy as sa
from alembic import op

revision = "e011d561b6c7"
down_revision = "7ded9e261229"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("user_maxes", sa.Column("exercise_name", sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column("user_maxes", "exercise_name")
