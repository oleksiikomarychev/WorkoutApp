"""enforce single active applied plan per user

Revision ID: d3a9c4b7e1f2
Revises: 8c3f4a1b2d9f
Create Date: 2026-01-02
"""

import sqlalchemy as sa
from alembic import op

revision = "d3a9c4b7e1f2"
down_revision = "8c3f4a1b2d9f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE applied_calendar_plans SET is_active = COALESCE(is_active, false)")

    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY user_id
                    ORDER BY start_date DESC NULLS LAST, id DESC
                ) AS rn
            FROM applied_calendar_plans
            WHERE is_active IS TRUE
        )
        UPDATE applied_calendar_plans p
        SET is_active = FALSE
        FROM ranked r
        WHERE p.id = r.id AND r.rn > 1
        """
    )

    op.alter_column(
        "applied_calendar_plans",
        "is_active",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text("true"),
    )

    op.create_index(
        "ux_applied_calendar_plans_active_user",
        "applied_calendar_plans",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )


def downgrade() -> None:
    op.drop_index(
        "ux_applied_calendar_plans_active_user",
        table_name="applied_calendar_plans",
    )

    op.alter_column(
        "applied_calendar_plans",
        "is_active",
        existing_type=sa.Boolean(),
        nullable=True,
        server_default=None,
    )
