"""
Initial schema for coach-service

Revision ID: 0001
Revises: 
Create Date: 2025-08-29
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # coach_client_links
    op.create_table(
        'coach_client_links',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('coach_user_id', sa.String(), nullable=False),
        sa.Column('client_user_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('pricing_plan_id', sa.String(), nullable=True),
        sa.Column('notes_short', sa.String(length=256), nullable=True),
        sa.Column('client_display_name', sa.String(length=80), nullable=True),
        sa.Column('client_avatar_url', sa.String(length=512), nullable=True),
        sa.UniqueConstraint('coach_user_id', 'client_user_id', name='uq_coach_client_unique'),
    )
    op.create_index('idx_ccl_coach', 'coach_client_links', ['coach_user_id'])
    op.create_index('idx_ccl_client', 'coach_client_links', ['client_user_id'])
    op.create_index('idx_ccl_status', 'coach_client_links', ['status'])

    # client_tags
    op.create_table(
        'client_tags',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('coach_user_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('color', sa.String(), nullable=True),
        sa.UniqueConstraint('coach_user_id', 'name', name='uq_tag_name_per_coach'),
    )
    op.create_index('idx_ct_coach', 'client_tags', ['coach_user_id'])
    op.create_index('idx_ct_name', 'client_tags', ['name'])

    # client_tag_links
    op.create_table(
        'client_tag_links',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('tag_id', sa.String(), nullable=False),
        sa.Column('client_user_id', sa.String(), nullable=False),
        sa.Column('coach_user_id', sa.String(), nullable=False),
        sa.UniqueConstraint('tag_id', 'client_user_id', 'coach_user_id', name='uq_tag_client_coach'),
    )
    op.create_index('idx_ctl_tag', 'client_tag_links', ['tag_id'])
    op.create_index('idx_ctl_client', 'client_tag_links', ['client_user_id'])
    op.create_index('idx_ctl_coach', 'client_tag_links', ['coach_user_id'])

    # client_notes
    op.create_table(
        'client_notes',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('coach_user_id', sa.String(), nullable=False),
        sa.Column('client_user_id', sa.String(), nullable=False),
        sa.Column('visibility', sa.String(), nullable=False, server_default='coach_only'),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_cn_coach', 'client_notes', ['coach_user_id'])
    op.create_index('idx_cn_client', 'client_notes', ['client_user_id'])
    op.create_index('idx_cn_created', 'client_notes', ['created_at'])

    # invitations
    op.create_table(
        'invitations',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('coach_user_id', sa.String(), nullable=False),
        sa.Column('email_or_user_id', sa.String(), nullable=False),
        sa.Column('code', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='sent'),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_inv_coach', 'invitations', ['coach_user_id'])
    op.create_index('idx_inv_status', 'invitations', ['status'])
    op.create_index('idx_inv_created', 'invitations', ['created_at'])
    op.create_index('idx_inv_code', 'invitations', ['code'], unique=True)


def downgrade() -> None:
    op.drop_index('idx_inv_code', table_name='invitations')
    op.drop_index('idx_inv_created', table_name='invitations')
    op.drop_index('idx_inv_status', table_name='invitations')
    op.drop_index('idx_inv_coach', table_name='invitations')
    op.drop_table('invitations')

    op.drop_index('idx_cn_created', table_name='client_notes')
    op.drop_index('idx_cn_client', table_name='client_notes')
    op.drop_index('idx_cn_coach', table_name='client_notes')
    op.drop_table('client_notes')

    op.drop_index('idx_ctl_coach', table_name='client_tag_links')
    op.drop_index('idx_ctl_client', table_name='client_tag_links')
    op.drop_index('idx_ctl_tag', table_name='client_tag_links')
    op.drop_table('client_tag_links')

    op.drop_index('idx_ct_name', table_name='client_tags')
    op.drop_index('idx_ct_coach', table_name='client_tags')
    op.drop_table('client_tags')

    op.drop_index('idx_ccl_status', table_name='coach_client_links')
    op.drop_index('idx_ccl_client', table_name='coach_client_links')
    op.drop_index('idx_ccl_coach', table_name='coach_client_links')
    op.drop_table('coach_client_links')
