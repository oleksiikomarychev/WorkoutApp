"""merge heads"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '60d14a510cba'
down_revision = ('2025_10_08_rename', '2025_10_12_add_user_id')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
