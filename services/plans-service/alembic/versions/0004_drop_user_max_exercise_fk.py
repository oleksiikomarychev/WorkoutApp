from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0004_drop_user_max_exercise_fk"
down_revision = "0003_applied_calendar_plans"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if "user_maxes" not in tables:
        # Fresh DB: just create table without FK
        op.create_table(
            "user_maxes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("exercise_id", sa.Integer(), nullable=False),
            sa.Column("max_weight", sa.Integer(), nullable=False),
            sa.Column("rep_max", sa.Integer(), nullable=False),
        )
        return

    # Table exists. Remove FK if present
    if dialect == "sqlite":
        # SQLite: recreate table without FK constraint on exercise_id
        op.execute("PRAGMA foreign_keys=OFF")

        # Create a new table without the FK
        op.create_table(
            "user_maxes_new",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("exercise_id", sa.Integer(), nullable=False),
            sa.Column("max_weight", sa.Integer(), nullable=False),
            sa.Column("rep_max", sa.Integer(), nullable=False),
        )
        # Copy data
        op.execute(
            "INSERT INTO user_maxes_new (id, exercise_id, max_weight, rep_max) "
            "SELECT id, exercise_id, max_weight, rep_max FROM user_maxes"
        )
        # Drop old and rename new
        op.drop_table("user_maxes")
        op.rename_table("user_maxes_new", "user_maxes")

        op.execute("PRAGMA foreign_keys=ON")
    else:
        # Other DBs: find and drop FK constraint on exercise_id
        fks = inspector.get_foreign_keys("user_maxes")
        for fk in fks:
            if "exercise_id" in fk.get("constrained_columns", []):
                # Drop the FK by discovered name
                if fk.get("name"):
                    op.drop_constraint(fk["name"], "user_maxes", type_="foreignkey")
                else:
                    # Fallback: attempt common default names
                    for guess in (
                        "user_maxes_exercise_id_fkey",
                        "fk_user_maxes_exercise_id_exercise_list",
                    ):
                        try:
                            op.drop_constraint(guess, "user_maxes", type_="foreignkey")
                            break
                        except Exception:
                            continue
                break


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        # Recreate table with FK back to exercise_list.id
        op.execute("PRAGMA foreign_keys=OFF")

        inspector = sa.inspect(bind)
        if "user_maxes" not in inspector.get_table_names():
            # If table somehow missing, recreate with FK
            op.create_table(
                "user_maxes",
                sa.Column("id", sa.Integer(), primary_key=True),
                sa.Column("exercise_id", sa.Integer(), nullable=False),
                sa.Column("max_weight", sa.Integer(), nullable=False),
                sa.Column("rep_max", sa.Integer(), nullable=False),
                sa.ForeignKeyConstraint(["exercise_id"], ["exercise_list.id"]),
            )
        else:
            op.create_table(
                "user_maxes_old",
                sa.Column("id", sa.Integer(), primary_key=True),
                sa.Column("exercise_id", sa.Integer(), nullable=False),
                sa.Column("max_weight", sa.Integer(), nullable=False),
                sa.Column("rep_max", sa.Integer(), nullable=False),
                sa.ForeignKeyConstraint(["exercise_id"], ["exercise_list.id"]),
            )
            op.execute(
                "INSERT INTO user_maxes_old (id, exercise_id, max_weight, rep_max) "
                "SELECT id, exercise_id, max_weight, rep_max FROM user_maxes"
            )
            op.drop_table("user_maxes")
            op.rename_table("user_maxes_old", "user_maxes")

        op.execute("PRAGMA foreign_keys=ON")
    else:
        # Re-add FK for non-SQLite DBs
        op.create_foreign_key(
            constraint_name="user_maxes_exercise_id_fkey",
            source_table="user_maxes",
            referent_table="exercise_list",
            local_cols=["exercise_id"],
            remote_cols=["id"],
        )
