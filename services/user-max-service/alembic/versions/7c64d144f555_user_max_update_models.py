"""user-max: update models

Revision ID: 7c64d144f555
Revises: 38182b4d2bca
Create Date: 2025-11-16 11:55:30.976764
"""

import sqlalchemy as sa
from alembic import op

revision = "7c64d144f555"
down_revision = "38182b4d2bca"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("user_maxes", schema=None) as batch_op:
            batch_op.add_column(sa.Column("source", sa.String(length=64), nullable=True))
            batch_op.alter_column(
                "max_weight",
                existing_type=sa.DOUBLE_PRECISION(precision=53),
                type_=sa.Integer(),
                existing_nullable=False,
            )
            batch_op.alter_column(
                "rep_max",
                existing_type=sa.INTEGER(),
                server_default=None,
                nullable=True,
            )
    else:
        op.add_column("user_maxes", sa.Column("source", sa.String(length=64), nullable=True))
        op.alter_column(
            "user_maxes",
            "max_weight",
            existing_type=sa.DOUBLE_PRECISION(precision=53),
            type_=sa.Integer(),
            existing_nullable=False,
        )
        op.alter_column("user_maxes", "rep_max", existing_type=sa.INTEGER(), server_default=None, nullable=True)
    op.create_index("idx_exercise_id", "user_maxes", ["exercise_id"], unique=False)
    op.create_index(op.f("ix_user_maxes_id"), "user_maxes", ["id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_user_maxes_id"), table_name="user_maxes")
    op.drop_index("idx_exercise_id", table_name="user_maxes")
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("user_maxes", schema=None) as batch_op:
            batch_op.alter_column(
                "rep_max",
                existing_type=sa.INTEGER(),
                server_default=sa.text("0"),
                nullable=False,
            )
            batch_op.alter_column(
                "max_weight",
                existing_type=sa.Integer(),
                type_=sa.DOUBLE_PRECISION(precision=53),
                existing_nullable=False,
            )
            batch_op.drop_column("source")
    else:
        op.alter_column(
            "user_maxes",
            "rep_max",
            existing_type=sa.INTEGER(),
            server_default=sa.text("0"),
            nullable=False,
        )
        op.alter_column(
            "user_maxes",
            "max_weight",
            existing_type=sa.Integer(),
            type_=sa.DOUBLE_PRECISION(precision=53),
            existing_nullable=False,
        )
        op.drop_column("user_maxes", "source")
