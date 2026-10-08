"""add gin"""

from alembic import op

# revision identifiers, used by Alembic.
revision = 'fa56159771df'
down_revision = 'c9da6c90978d'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_exercise_list_name_gin "
        "ON exercise_list USING gin (name gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_muscle_group_btree "
        "ON exercise_list (muscle_group)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_equipment_btree "
        "ON exercise_list (equipment)"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_equipment_btree")
    op.execute("DROP INDEX IF EXISTS ix_muscle_group_btree")
    op.execute("DROP INDEX IF EXISTS ix_exercise_list_name_gin")
