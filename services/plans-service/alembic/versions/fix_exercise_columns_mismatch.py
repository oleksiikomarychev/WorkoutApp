"""Fix column mismatch in plan_exercises table

Revision ID: fix_exercise_columns_mismatch
Revises: add_missing_cols_plan_exercises
Create Date: 2025-09-20 18:55:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "fix_exercise_columns_mismatch"
down_revision = "add_missing_cols_plan_exercises"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    result = conn.execute(
        sa.text(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'plan_exercises' AND table_schema = 'public'"
        )
    )
    existing_columns = [row[0] for row in result.fetchall()]

    if "exercise_id" in existing_columns and "exercise_definition_id" in existing_columns:
        op.alter_column("plan_exercises", "exercise_id", nullable=True)

        op.execute("UPDATE plan_exercises SET exercise_id = 1 WHERE exercise_id IS NULL")

        op.drop_column("plan_exercises", "exercise_id")


def downgrade():
    op.add_column("plan_exercises", sa.Column("exercise_id", sa.Integer(), nullable=True))
