"""add gin abd btree"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "c9da6c90978d"
down_revision = "2026_01_09_rest_seconds"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index("ix_exercise_list_name", table_name="exercise_list", if_exists=True)
    op.create_index(
        op.f("ix_exercise_list_root_exercise_id"),
        "exercise_list",
        ["root_exercise_id"],
        unique=False,
        if_not_exists=True,
    )


def downgrade():
    op.drop_index(op.f("ix_exercise_list_root_exercise_id"), table_name="exercise_list", if_exists=True)
    op.create_index("ix_exercise_list_name", "exercise_list", ["name"], unique=True)
