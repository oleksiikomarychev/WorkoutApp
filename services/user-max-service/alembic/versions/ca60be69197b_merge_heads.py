"""merge heads

Revision ID: ca60be69197b
Revises: 0001_initial_user_maxes, d1916f74abd6, manual_user_max_20250909_202242
Create Date: 2025-09-09 17:33:14.747819
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ca60be69197b'
down_revision = ('0001_initial_user_maxes', 'd1916f74abd6', 'manual_user_max_20250909_202242')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
