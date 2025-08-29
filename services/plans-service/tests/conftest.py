import os
import sys
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

# Ensure the service package is importable regardless of repo root cwd
SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))


@pytest.fixture(scope="session")
def test_db_url(tmp_path_factory) -> str:
    tmp_dir = tmp_path_factory.mktemp("plans_db")
    db_path = tmp_dir / "test_plans.db"
    return f"sqlite:///{db_path}"


@pytest.fixture(scope="session", autouse=True)
def migrated_db(test_db_url: str):
    # Set DATABASE_URL for alembic env and service code
    os.environ["DATABASE_URL"] = test_db_url
    cfg = Config(str(SERVICE_ROOT / "alembic.ini"))
    # Pin script_location explicitly to avoid picking up wrong migrations when running from repo root
    cfg.set_main_option("script_location", str(SERVICE_ROOT / "alembic"))
    command.upgrade(cfg, "head")
    yield test_db_url


@pytest.fixture()
def client(migrated_db: str):
    # Import after DATABASE_URL is set and migrations have run
    from plans_service.database import SessionLocal, get_db
    from plans_service.main import app

    # Override dependency to use the test session
    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    # Cleanup override
    app.dependency_overrides.pop(get_db, None)
