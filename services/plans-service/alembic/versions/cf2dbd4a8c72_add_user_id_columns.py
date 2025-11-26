"""Add user scoping columns"""

import sqlalchemy as sa
from alembic import op

revision = "cf2dbd4a8c72"
down_revision = "add_missing_cols_plan_exercises"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # calendar_plans.user_id
    with op.batch_alter_table("calendar_plans", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "user_id",
                sa.String(length=255),
                nullable=False,
                server_default=sa.text("'legacy-user'"),
            )
        )
        batch_op.create_index(
            "ix_calendar_plans_user_id",
            ["user_id"],
            unique=False,
        )

    # applied_calendar_plans.user_id
    with op.batch_alter_table("applied_calendar_plans", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "user_id",
                sa.String(length=255),
                nullable=False,
                server_default=sa.text("'legacy-user'"),
            )
        )
        batch_op.create_index(
            "ix_applied_calendar_plans_user_id",
            ["user_id"],
            unique=False,
        )

    # drop defaults after backfill
    with op.batch_alter_table("calendar_plans", schema=None) as batch_op:
        batch_op.alter_column(
            "user_id",
            server_default=None,
            existing_type=sa.String(length=255),
        )

    with op.batch_alter_table("applied_calendar_plans", schema=None) as batch_op:
        batch_op.alter_column(
            "user_id",
            server_default=None,
            existing_type=sa.String(length=255),
        )


def downgrade() -> None:
    with op.batch_alter_table("applied_calendar_plans", schema=None) as batch_op:
        batch_op.drop_index("ix_applied_calendar_plans_user_id")
        batch_op.drop_column("user_id")

    with op.batch_alter_table("calendar_plans", schema=None) as batch_op:
        batch_op.drop_index("ix_calendar_plans_user_id")
        batch_op.drop_column("user_id")
