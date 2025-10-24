"""Add user_id columns to workouts, workout_exercises, and workout_sessions

Revision ID: 2025_10_12_add_user_id
Revises: c1d2e3f4a5b6
Create Date: 2025-10-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2025_10_12_add_user_id'
down_revision = 'c1d2e3f4a5b6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE workouts
        ADD COLUMN user_id VARCHAR(255) NOT NULL DEFAULT 'legacy-user'
        """
    )
    op.execute("CREATE INDEX ix_workouts_user_id ON workouts (user_id)")
    op.execute("ALTER TABLE workouts ALTER COLUMN user_id DROP DEFAULT")

    op.execute(
        """
        ALTER TABLE workout_exercises
        ADD COLUMN user_id VARCHAR(255) NOT NULL DEFAULT 'legacy-user'
        """
    )
    op.execute("CREATE INDEX ix_workout_exercises_user_id ON workout_exercises (user_id)")
    op.execute("ALTER TABLE workout_exercises ALTER COLUMN user_id DROP DEFAULT")

    op.execute(
        """
        ALTER TABLE workout_sessions
        ADD COLUMN user_id VARCHAR(255) NOT NULL DEFAULT 'legacy-user'
        """
    )
    op.execute("CREATE INDEX ix_workout_sessions_user_id ON workout_sessions (user_id)")
    op.execute("ALTER TABLE workout_sessions ALTER COLUMN user_id DROP DEFAULT")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_workout_sessions_user_id")
    op.execute(
        """
        ALTER TABLE workout_sessions
        DROP COLUMN IF EXISTS user_id
        """
    )

    op.execute("DROP INDEX IF EXISTS ix_workout_exercises_user_id")
    op.execute(
        """
        ALTER TABLE workout_exercises
        DROP COLUMN IF EXISTS user_id
        """
    )

    op.execute("DROP INDEX IF EXISTS ix_workouts_user_id")
    op.execute(
        """
        ALTER TABLE workouts
        DROP COLUMN IF EXISTS user_id
        """
    )
