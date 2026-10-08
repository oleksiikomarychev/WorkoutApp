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
        print(f"Migration failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(run_migrations())
