from backend_common.dependencies import make_get_current_user_id, make_get_db_sync
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .config import settings

engine = create_engine(settings.agent_database_url)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


get_db = make_get_db_sync(SessionLocal)
get_current_user_id = make_get_current_user_id("agent-service")
