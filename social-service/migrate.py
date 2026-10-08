"""Database migration script."""
import sys

from alembic import command
from alembic.config import Config


def run_migrations():
    """Run database migrations."""
    alembic_cfg = Config("alembic.ini")
    
    try:
        print("Running database migrations...")
        command.upgrade(alembic_cfg, "head")
        print("Migrations completed successfully!")
        return 0
    except Exception as e:
        print(f"Migration failed: {e}", file=sys.stderr)
        return 1


def rollback_migration():
    """Rollback last migration."""
    alembic_cfg = Config("alembic.ini")
    
    try:
        print("Rolling back last migration...")
        command.downgrade(alembic_cfg, "-1")
        print("Rollback completed successfully!")
        return 0
    except Exception as e:
        print(f"Rollback failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        sys.exit(rollback_migration())
    else:
        sys.exit(run_migrations())
