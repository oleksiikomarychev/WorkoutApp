from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_calendar_plan_instances"
down_revision = "0001_calendar_plans"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "calendar_plan_instances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_plan_id", sa.Integer(), sa.ForeignKey("calendar_plans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("schedule", sa.Text(), nullable=False),
        sa.Column("duration_weeks", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("calendar_plan_instances")
