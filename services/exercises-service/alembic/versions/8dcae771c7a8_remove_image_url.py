"""remove image_url"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8dcae771c7a8"
down_revision = "042135cf4676"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("exercise_list", "image_url")


def downgrade():
    op.add_column("exercise_list", sa.Column("image_url", sa.VARCHAR(length=512), autoincrement=False, nullable=True))
