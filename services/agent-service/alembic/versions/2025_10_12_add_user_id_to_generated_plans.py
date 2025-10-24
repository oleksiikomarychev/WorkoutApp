"""add user_id to generated_plans

Revision ID: g1h2i3j4k5l6
Revises: 9fa19f5392f3
Create Date: 2025-10-12 22:40:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "g1h2i3j4k5l6"
down_revision = "9fa19f5392f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add user_id column with default value for backfill
    with op.batch_alter_table("generated_plans", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "user_id",
                sa.String(length=255),
                nullable=False,
                server_default=sa.text("'legacy-user'"),
            )
        )
    
    # Add index on user_id for filtering
    op.create_index(
        "ix_generated_plans_user_id",
        "generated_plans",
        ["user_id"],
        unique=False,
    )
    
    # Drop the default value after backfill
    with op.batch_alter_table("generated_plans", schema=None) as batch_op:
        batch_op.alter_column(
            "user_id",
            server_default=None,
            existing_type=sa.String(length=255),
        )


def downgrade() -> None:
    op.drop_index("ix_generated_plans_user_id", table_name="generated_plans")
    
    with op.batch_alter_table("generated_plans", schema=None) as batch_op:
        batch_op.drop_column("user_id")
