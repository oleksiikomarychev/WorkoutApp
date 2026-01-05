"""Initial migration

Revision ID: d1916f74abd6
Revises:
Create Date: 2025-09-05 16:44:44.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "d1916f74abd6"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("user_maxes"):
        existing_columns = {c["name"] for c in inspector.get_columns("user_maxes")}

        with op.batch_alter_table("user_maxes", schema=None) as batch_op:
            if "user_id" not in existing_columns:
                batch_op.add_column(
                    sa.Column(
                        "user_id",
                        sa.Integer,
                        nullable=False,
                        server_default=sa.text("0"),
                    )
                )

            if "date" not in existing_columns:
                batch_op.add_column(
                    sa.Column(
                        "date",
                        sa.Date,
                        nullable=False,
                        server_default=sa.text("'1970-01-01'"),
                    )
                )

        return

    op.create_table(
        "user_maxes",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("exercise_id", sa.Integer, nullable=False),
        sa.Column("max_weight", sa.Integer, nullable=False),
        sa.Column("rep_max", sa.Integer, nullable=False),
        sa.Column("date", sa.Date, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("user_maxes")
