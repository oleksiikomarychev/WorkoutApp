"""crm: add note column to coach_athlete_links"""

import sqlalchemy as sa
from alembic import op

revision = "20251123_add_note_to_links"
down_revision = "20251123_crm_restore_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = {col["name"] for col in insp.get_columns("coach_athlete_links")}
    if "note" not in columns:
        op.add_column("coach_athlete_links", sa.Column("note", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    columns = {col["name"] for col in insp.get_columns("coach_athlete_links")}
    if "note" in columns:
        op.drop_column("coach_athlete_links", "note")
