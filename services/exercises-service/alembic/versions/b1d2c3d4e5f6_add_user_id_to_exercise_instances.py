"""add user_id to exercise_instances

Revision ID: b1d2c3d4e5f6
Revises: 7076299de40a
Create Date: 2025-10-12 17:02:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b1d2c3d4e5f6"
down_revision = "7076299de40a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("exercise_instances", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "user_id",
                sa.String(length=255),
                nullable=False,
                server_default=sa.text("'legacy-user'"),
            )
        )

    with op.batch_alter_table("exercise_instances", schema=None) as batch_op:
        batch_op.alter_column(
            "user_id",
            server_default=None,
            existing_type=sa.String(length=255),
        )


def downgrade() -> None:
    with op.batch_alter_table("exercise_instances", schema=None) as batch_op:
        batch_op.drop_column("user_id")
