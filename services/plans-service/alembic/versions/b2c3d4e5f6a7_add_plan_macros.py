"""add plan_macros table

Revision ID: b2c3d4e5f6a7
Revises: a1bb8d63a109
Create Date: 2025-10-27 14:35:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "a1bb8d63a109"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "plan_macros",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "calendar_plan_id",
            sa.Integer(),
            sa.ForeignKey("calendar_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("rule_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_plan_macros_id", "plan_macros", ["id"], unique=False)
    op.create_index("ix_plan_macros_calendar_plan_id", "plan_macros", ["calendar_plan_id"], unique=False)


def downgrade():
    op.drop_index("ix_plan_macros_calendar_plan_id", table_name="plan_macros")
    op.drop_index("ix_plan_macros_id", table_name="plan_macros")
    op.drop_table("plan_macros")
