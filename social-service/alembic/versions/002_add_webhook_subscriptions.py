"""Add webhook subscriptions table

Revision ID: 002
Revises: 001
Create Date: 2025-11-07 12:00:00.000000

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: str | None = '001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create webhook_subscriptions table
    op.create_table(
        'webhook_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('service', sa.String(length=50), nullable=False),
        sa.Column('target_url', sa.String(length=2048), nullable=False),
        sa.Column('secret', sa.String(length=255), nullable=False),
        sa.Column('events', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('filters', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('active', sa.String(length=10), nullable=False),
        sa.Column('lease_expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_webhook_subscriptions_active', 'webhook_subscriptions', ['active', 'service'], unique=False)
    op.create_index(op.f('ix_webhook_subscriptions_created_at'), 'webhook_subscriptions', ['created_at'], unique=False)


def downgrade() -> None:
    # Drop webhook_subscriptions table
    op.drop_index(op.f('ix_webhook_subscriptions_created_at'), table_name='webhook_subscriptions')
    op.drop_index('idx_webhook_subscriptions_active', table_name='webhook_subscriptions')
    op.drop_table('webhook_subscriptions')
