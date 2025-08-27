"""Generic Alembic migration script template for exercises-service"""
from alembic import op
import sqlalchemy as sa
import json

revision = ${repr(revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}

def upgrade():
    pass

def downgrade():
    pass
