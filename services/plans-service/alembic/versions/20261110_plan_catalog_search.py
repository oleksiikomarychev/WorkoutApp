"""Add catalog search indexes without changing plan data or metadata codes."""
from alembic import op

revision = '20261110_plan_catalog'
down_revision = '26d1a3bd8193'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
    # CONCURRENTLY avoids holding a write-blocking lock while indexing plans.
    with op.get_context().autocommit_block():
        op.execute("""CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_calendar_plans_catalog_fts
            ON calendar_plans USING gin
            (to_tsvector('simple'::regconfig, coalesce(name, '') || ' ' || coalesce(notes, '')))
            WHERE id = root_plan_id""")
        op.execute("""CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_calendar_plans_catalog_trgm
            ON calendar_plans USING gin (name gin_trgm_ops)
            WHERE id = root_plan_id""")


def downgrade():
    with op.get_context().autocommit_block():
        op.execute('DROP INDEX CONCURRENTLY IF EXISTS ix_calendar_plans_catalog_trgm')
        op.execute('DROP INDEX CONCURRENTLY IF EXISTS ix_calendar_plans_catalog_fts')
    # pg_trgm may be shared with other features; leave the extension installed.
