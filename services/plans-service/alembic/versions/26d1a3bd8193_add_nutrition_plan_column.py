"""add_nutrition_plan_column

Revision ID: 26d1a3bd8193
Revises: 878e898d470a
Create Date: 2026-04-17 15:17:41.600171
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "26d1a3bd8193"
down_revision = "878e898d470a"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("applied_plan_workouts", sa.Column("nutrition_plan", sa.JSON(), nullable=True))
    op.add_column("calendar_plans", sa.Column("nutrition_plan", sa.JSON(), nullable=True))
    op.alter_column("calendar_plans", "root_plan_id", existing_type=sa.INTEGER(), nullable=False)
    op.add_column("plan_workouts", sa.Column("nutrition_plan", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("plan_workouts", "nutrition_plan")
    op.alter_column("calendar_plans", "root_plan_id", existing_type=sa.INTEGER(), nullable=True)
    op.drop_column("calendar_plans", "nutrition_plan")
    op.drop_column("applied_plan_workouts", "nutrition_plan")
