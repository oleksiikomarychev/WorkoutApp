"""Add root_plan_id to calendar plans

Revision ID: add_root_plan_id_to_calendar_plans
Revises: add_missing_cols_plan_exercises
Create Date: 2025-10-24 14:51:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "add_root_plan_id_to_calendar_pl"
down_revision = "add_missing_cols_plan_exercises"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "calendar_plans",
        sa.Column("root_plan_id", sa.Integer(), nullable=True),
    )

    conn = op.get_bind()
    conn.execute(sa.text("UPDATE calendar_plans SET root_plan_id = id WHERE root_plan_id IS NULL"))

    # Enforce NOT NULL and add FK + index
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_calendar_plan_root()
        RETURNS trigger AS $$
        BEGIN
            IF NEW.root_plan_id IS NULL THEN
                NEW.root_plan_id := NEW.id;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_set_calendar_plan_root
        BEFORE INSERT ON calendar_plans
        FOR EACH ROW
        EXECUTE FUNCTION set_calendar_plan_root();
        """
    )

    op.alter_column("calendar_plans", "root_plan_id", nullable=False)

    op.create_foreign_key(
        "fk_calendar_plans_root_plan",
        "calendar_plans",
        "calendar_plans",
        ["root_plan_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_calendar_plans_root_plan_id",
        "calendar_plans",
        ["root_plan_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_calendar_plans_root_plan_id", table_name="calendar_plans")
    op.drop_constraint("fk_calendar_plans_root_plan", "calendar_plans", type_="foreignkey")
    op.execute("DROP TRIGGER IF EXISTS trg_set_calendar_plan_root ON calendar_plans")
    op.execute("DROP FUNCTION IF EXISTS set_calendar_plan_root()")
    op.drop_column("calendar_plans", "root_plan_id")
