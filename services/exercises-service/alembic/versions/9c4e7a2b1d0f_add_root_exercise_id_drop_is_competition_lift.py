"""add root_exercise_id to exercise_list and drop is_competition_lift

Revision ID: 9c4e7a2b1d0f
Revises: f7a1b2c3d4e5
Create Date: 2025-12-13 21:51:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "9c4e7a2b1d0f"
down_revision = "f7a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("exercise_list", schema=None) as batch_op:
        batch_op.add_column(sa.Column("root_exercise_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_exercise_list_root_exercise_id",
            "exercise_list",
            ["root_exercise_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.drop_column("is_competition_lift")


def downgrade() -> None:
    with op.batch_alter_table("exercise_list", schema=None) as batch_op:
        batch_op.add_column(sa.Column("is_competition_lift", sa.Integer(), nullable=True))
        batch_op.drop_constraint("fk_exercise_list_root_exercise_id", type_="foreignkey")
        batch_op.drop_column("root_exercise_id")
