"""add_applied_hierarchy_models

Revision ID: 7bbaddb6e0d7
Revises: edef306332ff
Create Date: 2025-09-17 03:06:52.583179
"""

import sqlalchemy as sa
from alembic import op

revision = "7bbaddb6e0d7"
down_revision = "edef306332ff"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "applied_mesocycles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("applied_plan_id", sa.Integer(), nullable=False),
        sa.Column("mesocycle_id", sa.Integer(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["applied_plan_id"],
            ["applied_calendar_plans.id"],
        ),
        sa.ForeignKeyConstraint(
            ["mesocycle_id"],
            ["mesocycles.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_applied_mesocycles_id"), "applied_mesocycles", ["id"], unique=False)
    op.create_table(
        "applied_microcycles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("applied_mesocycle_id", sa.Integer(), nullable=False),
        sa.Column("microcycle_id", sa.Integer(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["applied_mesocycle_id"],
            ["applied_mesocycles.id"],
        ),
        sa.ForeignKeyConstraint(
            ["microcycle_id"],
            ["microcycles.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_applied_microcycles_id"), "applied_microcycles", ["id"], unique=False)
    op.create_table(
        "applied_workouts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("applied_microcycle_id", sa.Integer(), nullable=False),
        sa.Column("workout_id", sa.Integer(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["applied_microcycle_id"],
            ["applied_microcycles.id"],
        ),
        sa.ForeignKeyConstraint(
            ["workout_id"],
            ["workouts.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_applied_workouts_id"), "applied_workouts", ["id"], unique=False)
    op.alter_column(
        "applied_calendar_plans",
        "start_date",
        nullable=True,
        existing_server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    op.drop_index("ix_applied_calendar_plans_user_id", table_name="applied_calendar_plans")
    op.add_column("calendar_plans", sa.Column("schedule", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("calendar_plans", "schedule")
    op.create_index("ix_applied_calendar_plans_user_id", "applied_calendar_plans", ["user_id"], unique=False)
    op.alter_column(
        "applied_calendar_plans",
        "start_date",
        nullable=False,
        existing_server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    op.drop_index(op.f("ix_applied_workouts_id"), table_name="applied_workouts")
    op.drop_table("applied_workouts")
    op.drop_index(op.f("ix_applied_microcycles_id"), table_name="applied_microcycles")
    op.drop_table("applied_microcycles")
    op.drop_index(op.f("ix_applied_mesocycles_id"), table_name="applied_mesocycles")
    op.drop_table("applied_mesocycles")
