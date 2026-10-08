"""Add rest_seconds and notes to plan_exercises"""

import sqlalchemy as sa
from alembic import op

revision = "20260113_rest_notes_on_plan_exercises"
down_revision = "add_is_public_to_calendar_plans"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("plan_exercises", sa.Column("rest_seconds", sa.Integer(), nullable=True))
    op.add_column("plan_exercises", sa.Column("notes", sa.String(length=512), nullable=True))


def downgrade():
    op.drop_column("plan_exercises", "notes")
    op.drop_column("plan_exercises", "rest_seconds")
