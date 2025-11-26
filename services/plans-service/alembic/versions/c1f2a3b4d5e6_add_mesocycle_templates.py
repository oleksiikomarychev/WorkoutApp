"""add mesocycle and microcycle templates tables

Revision ID: c1f2a3b4d5e6
Revises: b2c3d4e5f6a7
Create Date: 2025-10-28 04:36:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c1f2a3b4d5e6"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # mesocycle_templates
    if "mesocycle_templates" not in insp.get_table_names():
        op.create_table(
            "mesocycle_templates",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("user_id", sa.String(length=255), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("notes", sa.String(length=255), nullable=True),
            sa.Column("weeks_count", sa.Integer(), nullable=True),
            sa.Column("microcycle_length_days", sa.Integer(), nullable=True),
            sa.Column("normalization_value", sa.Integer(), nullable=True),
            sa.Column("normalization_unit", sa.String(length=16), nullable=True),
            sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
    # ensure indexes exist
    existing_meso_idx = (
        {ix["name"] for ix in insp.get_indexes("mesocycle_templates")}
        if "mesocycle_templates" in insp.get_table_names()
        else set()
    )
    if "ix_mesocycle_templates_id" not in existing_meso_idx:
        try:
            op.create_index("ix_mesocycle_templates_id", "mesocycle_templates", ["id"], unique=False)
        except Exception:
            pass
    if "ix_mesocycle_templates_user_id" not in existing_meso_idx:
        try:
            op.create_index("ix_mesocycle_templates_user_id", "mesocycle_templates", ["user_id"], unique=False)
        except Exception:
            pass

    # microcycle_templates
    if "microcycle_templates" not in insp.get_table_names():
        op.create_table(
            "microcycle_templates",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column(
                "mesocycle_template_id",
                sa.Integer(),
                sa.ForeignKey("mesocycle_templates.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("notes", sa.String(length=255), nullable=True),
            sa.Column("order_index", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("days_count", sa.Integer(), nullable=True),
            sa.Column("schedule_json", sa.JSON(), nullable=True),
        )
    existing_micro_idx = (
        {ix["name"] for ix in insp.get_indexes("microcycle_templates")}
        if "microcycle_templates" in insp.get_table_names()
        else set()
    )
    if "ix_microcycle_templates_id" not in existing_micro_idx:
        try:
            op.create_index("ix_microcycle_templates_id", "microcycle_templates", ["id"], unique=False)
        except Exception:
            pass
    if "ix_microcycle_templates_mesocycle_template_id" not in existing_micro_idx:
        try:
            op.create_index(
                "ix_microcycle_templates_mesocycle_template_id",
                "microcycle_templates",
                ["mesocycle_template_id"],
                unique=False,
            )
        except Exception:
            pass


def downgrade():
    op.drop_index("ix_microcycle_templates_mesocycle_template_id", table_name="microcycle_templates")
    op.drop_index("ix_microcycle_templates_id", table_name="microcycle_templates")
    op.drop_table("microcycle_templates")

    op.drop_index("ix_mesocycle_templates_user_id", table_name="mesocycle_templates")
    op.drop_index("ix_mesocycle_templates_id", table_name="mesocycle_templates")
    op.drop_table("mesocycle_templates")
