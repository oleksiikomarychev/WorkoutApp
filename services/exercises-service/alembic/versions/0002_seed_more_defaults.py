"""seed missing default exercises if not present

Revision ID: 0002_seed_more_defaults
Revises: 0001_initial_exercises
Create Date: 2025-08-27 11:05:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0002_seed_more_defaults'
down_revision: Union[str, None] = '0001_initial_exercises'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    meta = sa.MetaData()
    insp = sa.inspect(bind)

    if not insp.has_table('exercise_list'):
        return

    exercise_list = sa.Table('exercise_list', meta, autoload_with=bind)

    existing_names = set(
        name for (name,) in bind.execute(sa.select(exercise_list.c.name)).all()
    )

    rows = []
    if 'Back Squat' not in existing_names:
        rows.append({
            'name': 'Back Squat',
            'muscle_group': 'legs',
            'equipment': 'barbell',
            'target_muscles': ['quadriceps', 'glutes'],
            'synergist_muscles': ['hamstrings', 'erectors'],
            'movement_type': 'compound',
            'region': 'lower',
        })
    if 'Bench Press' not in existing_names:
        rows.append({
            'name': 'Bench Press',
            'muscle_group': 'chest',
            'equipment': 'barbell',
            'target_muscles': ['pectoralis major'],
            'synergist_muscles': ['triceps', 'anterior deltoid'],
            'movement_type': 'compound',
            'region': 'upper',
        })
    if 'Deadlift' not in existing_names:
        rows.append({
            'name': 'Deadlift',
            'muscle_group': 'back',
            'equipment': 'barbell',
            'target_muscles': ['erectors', 'glutes', 'hamstrings'],
            'synergist_muscles': ['forearms', 'lats'],
            'movement_type': 'compound',
            'region': 'lower',
        })

    if rows:
        op.bulk_insert(exercise_list, rows)


def downgrade() -> None:
    # Do not remove seeded rows on downgrade to avoid deleting potential user data.
    pass
