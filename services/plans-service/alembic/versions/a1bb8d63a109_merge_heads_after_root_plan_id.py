"""merge heads after root_plan_id

Revision ID: a1bb8d63a109
Revises: 7efa97188bad, add_root_plan_id_to_calendar_pl
Create Date: 2025-10-24 15:31:49.502823
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1bb8d63a109'
down_revision = ('7efa97188bad', 'add_root_plan_id_to_calendar_pl')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
