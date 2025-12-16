"""Add plan_adopters table for unique plan adoption tracking

Revision ID: 8c3f4a1b2d9e
Revises: add_is_public_to_calendar_plans
Create Date: 2025-12-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8c3f4a1b2d9e"
down_revision: str | None = "add_is_public_to_calendar_plans"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "plan_adopters",
        sa.Column("root_plan_id", sa.Integer(), nullable=False),
        sa.Column("adopter_user_id", sa.String(length=255), nullable=False),
        sa.Column("first_applied_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["root_plan_id"],
            ["calendar_plans.id"],
            name="fk_plan_adopters_root_plan_id_calendar_plans",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("root_plan_id", "adopter_user_id", name="pk_plan_adopters"),
    )

    op.create_index(
        "ix_plan_adopters_root_plan_id",
        "plan_adopters",
        ["root_plan_id"],
        unique=False,
    )
    op.create_index(
        "ix_plan_adopters_adopter_user_id",
        "plan_adopters",
        ["adopter_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_plan_adopters_adopter_user_id", table_name="plan_adopters")
    op.drop_index("ix_plan_adopters_root_plan_id", table_name="plan_adopters")
    op.drop_table("plan_adopters")
