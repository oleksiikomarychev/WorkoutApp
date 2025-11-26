import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "9fa19f5392f3"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "generated_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("plan_data", sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("generated_plans")
