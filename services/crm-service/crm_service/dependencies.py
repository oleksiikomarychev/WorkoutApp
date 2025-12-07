from backend_common.dependencies import make_get_current_user_id, make_get_db_async

from .database import AsyncSessionLocal

get_db = make_get_db_async(AsyncSessionLocal)
get_current_user_id = make_get_current_user_id("crm-service")
