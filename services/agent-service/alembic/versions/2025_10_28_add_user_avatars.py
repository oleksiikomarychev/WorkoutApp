"""
add user_avatars table to store PNG avatars by user_id

Revision ID: 2025_10_28_add_user_avatars
Revises: 
Create Date: 2025-10-28
"""
from alembic import op
import sqlalchemy as sa
# revision identifiers, used by Alembic.
revision = '2025_10_28_add_user_avatars'
down_revision = 'g1h2i3j4k5l6'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'user_avatars',
        sa.Column('user_id', sa.String(length=255), primary_key=True, nullable=False),
        sa.Column('content_type', sa.String(length=64), nullable=False, server_default='image/png'),
        sa.Column('image', sa.LargeBinary(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('ix_user_avatars_user_id', 'user_avatars', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_user_avatars_user_id', table_name='user_avatars')
    op.drop_table('user_avatars')
