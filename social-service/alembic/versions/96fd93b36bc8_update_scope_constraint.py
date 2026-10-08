"""update_scope_constraint

Revision ID: 96fd93b36bc8
Revises: 003_create_outbox_events
Create Date: 2025-11-22 07:15:58.996294

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '96fd93b36bc8'
down_revision: str | None = '003_create_outbox_events'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Clean up invalid data first
    op.execute("DELETE FROM posts WHERE scope = 'coach_only'")
    
    op.drop_constraint('posts_scope_check', 'posts', type_='check')
    op.create_check_constraint('posts_scope_check', 'posts', "scope IN ('public', 'followers', 'private')")


def downgrade() -> None:
    op.drop_constraint('posts_scope_check', 'posts', type_='check')
    op.create_check_constraint('posts_scope_check', 'posts', "scope IN ('public', 'followers', 'private', 'coach_only')")
