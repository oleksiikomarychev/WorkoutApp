"""accounts: stub for lost autogen migration 8b57bf954ef7

This migration was originally generated automatically and applied inside the
Docker container. When we started mounting ./alembic as a volume, the original
script was lost, but the revision id remained in the database. This file
recreates a no-op placeholder so Alembic can resolve the revision graph.
"""

import sqlalchemy as sa  # noqa: F401
from alembic import op

# revision identifiers, used by Alembic.
revision = "8b57bf954ef7"
down_revision = "20251123_display_name_not_null"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """No-op placeholder.

    The database is already at this revision; the original operations are
    unknown and would be lossy to reapply. We keep this as an anchor so
    subsequent migrations can safely build on top of it.
    """
    pass


def downgrade() -> None:
    """No-op downgrade.

    The original downgrade was lost and restoring it would be unsafe.
    """
    pass
