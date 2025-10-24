"""add user_id to user_maxes

Revision ID: f1g2h3i4j5k6
Revises: ca60be69197b
Create Date: 2025-10-12 22:35:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f1g2h3i4j5k6"
down_revision = "ca60be69197b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column_info["name"]: column_info for column_info in inspector.get_columns("user_maxes")}
    created_column = False

    if "user_id" not in columns:
        with op.batch_alter_table("user_maxes", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "user_id",
                    sa.String(length=255),
                    nullable=False,
                    server_default=sa.text("'legacy-user'"),
                )
            )
        created_column = True
    else:
        column_info = columns["user_id"]
        if not isinstance(column_info["type"], sa.String):
            with op.batch_alter_table("user_maxes", schema=None) as batch_op:
                batch_op.alter_column(
                    "user_id",
                    existing_type=column_info["type"],
                    type_=sa.String(length=255),
                    existing_nullable=column_info["nullable"],
                    postgresql_using="user_id::text",
                )

        op.execute(sa.text("UPDATE user_maxes SET user_id = 'legacy-user' WHERE user_id IS NULL"))

        with op.batch_alter_table("user_maxes", schema=None) as batch_op:
            batch_op.alter_column(
                "user_id",
                existing_type=sa.String(length=255),
                nullable=False,
            )

    existing_indexes = {index["name"] for index in inspector.get_indexes("user_maxes")}
    if "ix_user_maxes_user_id" not in existing_indexes:
        op.create_index(
            "ix_user_maxes_user_id",
            "user_maxes",
            ["user_id"],
            unique=False,
        )

    if "ix_user_maxes_unique_entry" not in existing_indexes:
        op.create_index(
            "ix_user_maxes_unique_entry",
            "user_maxes",
            ["user_id", "exercise_id", "rep_max", "date"],
            unique=True,
        )

    if created_column:
        with op.batch_alter_table("user_maxes", schema=None) as batch_op:
            batch_op.alter_column(
                "user_id",
                server_default=None,
                existing_type=sa.String(length=255),
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_indexes = {index["name"] for index in inspector.get_indexes("user_maxes")}
    if "ix_user_maxes_unique_entry" in existing_indexes:
        op.drop_index("ix_user_maxes_unique_entry", table_name="user_maxes")

    if "ix_user_maxes_user_id" in existing_indexes:
        op.drop_index("ix_user_maxes_user_id", table_name="user_maxes")

    columns = {column_info["name"]: column_info for column_info in inspector.get_columns("user_maxes")}
    if "user_id" in columns:
        column_info = columns["user_id"]
        if isinstance(column_info["type"], sa.String) and column_info["type"].length == 255:
            with op.batch_alter_table("user_maxes", schema=None) as batch_op:
                batch_op.alter_column(
                    "user_id",
                    existing_type=sa.String(length=255),
                    nullable=True,
                )
        else:
            with op.batch_alter_table("user_maxes", schema=None) as batch_op:
                batch_op.alter_column(
                    "user_id",
                    existing_type=column_info["type"],
                    nullable=True,
                )
