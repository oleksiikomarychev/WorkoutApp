"""exercises: update models"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '037701b3abb6'
down_revision = 'c1d2e3f4g5h6'
branch_labels = None
depends_on = None


CONSTRAINT_NAME = "exercise_instances_exercise_list_id_fkey"


def upgrade():
    # Перед созданием внешнего ключа удаляем "сиротские" записи,
    # которые ссылаются на отсутствующие exercise_list.id
    op.execute(
        sa.text(
            """
            DELETE FROM exercise_instances
            WHERE exercise_list_id NOT IN (SELECT id FROM exercise_list)
            """
        )
    )

    # Теперь можно безопасно создать внешний ключ
    op.create_foreign_key(
        CONSTRAINT_NAME,
        source_table="exercise_instances",
        referent_table="exercise_list",
        local_cols=["exercise_list_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )


def downgrade():
    # Удаляем FK и возвращаем прежние индексы
    op.drop_constraint(CONSTRAINT_NAME, "exercise_instances", type_="foreignkey")
    op.create_index(
        "ix_exercise_instances_user_workout",
        "exercise_instances",
        ["user_id", "workout_id"],
        unique=False,
    )
    op.create_index(
        "ix_exercise_instances_user_id",
        "exercise_instances",
        ["user_id"],
        unique=False,
    )
