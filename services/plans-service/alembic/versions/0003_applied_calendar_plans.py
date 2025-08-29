from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003_applied_calendar_plans"
down_revision = "0002_calendar_plan_instances"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "applied_calendar_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "calendar_plan_id",
            sa.Integer(),
            sa.ForeignKey("calendar_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "start_date", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "end_date", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.sql.expression.true(),
        ),
    )
    op.create_table(
        "applied_calendar_plan_user_maxes",
        sa.Column(
            "applied_calendar_plan_id",
            sa.Integer(),
            sa.ForeignKey("applied_calendar_plans.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("user_max_id", sa.Integer(), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("applied_calendar_plan_user_maxes")
    op.drop_table("applied_calendar_plans")
