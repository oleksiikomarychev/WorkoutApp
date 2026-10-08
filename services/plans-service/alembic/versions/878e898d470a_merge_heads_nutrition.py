"""merge_heads_nutrition

Revision ID: 878e898d470a
Revises: 20260113_rest_notes_on_plan_exercises, 20260201_add_set_type_and_subsets_to_plan_sets
Create Date: 2026-04-17 15:17:35.732862
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '878e898d470a'
down_revision = ('20260113_rest_notes_on_plan_exercises', '20260201_add_set_type_and_subsets_to_plan_sets')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
