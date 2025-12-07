from backend_common.dependencies import make_get_current_user_id

get_current_user_id = make_get_current_user_id("workouts-service", header_name="X-User-Id")
