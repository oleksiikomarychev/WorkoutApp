"""merge heads after adding exercise category fields

This migration merges the two branches that end at
- d46e5016a4df (exercises: update models)
- e1f2a3b4c5d6 (add exercise category fields)

so that Alembic again has a single head revision.
"""

revision = "f7a1b2c3d4e5"
down_revision = ("d46e5016a4df", "e1f2a3b4c5d6")
branch_labels = None
depends_on = None


def upgrade() -> None:  # type: ignore[override]
    # No-op merge migration.
    # Both parent branches must already be applied; this revision
    # simply tells Alembic that they converge into a single head.
    pass


def downgrade() -> None:  # type: ignore[override]
    # No-op downgrade for the merge; leaving both branches applied.
    # In practice you normally wouldn't downgrade past this point
    # without manual intervention.
    pass
