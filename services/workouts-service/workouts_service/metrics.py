from prometheus_client import Counter

WORKOUTS_CREATED_TOTAL = Counter(
    "workouts_created_total",
    "Number of workouts created in workouts-service",
    ["source"],  # manual | batch | generated
)

WORKOUT_SESSIONS_STARTED_TOTAL = Counter(
    "workout_sessions_started_total",
    "Number of workout sessions started in workouts-service",
)

WORKOUT_SESSIONS_FINISHED_TOTAL = Counter(
    "workout_sessions_finished_total",
    "Number of workout sessions finished in workouts-service",
)

GENERATED_WORKOUTS_CREATED_TOTAL = Counter(
    "generated_workouts_created_total",
    "Number of generated workouts created in workouts-service",
)

WORKOUT_CACHE_HITS_TOTAL = Counter(
    "workout_cache_hits_total",
    "Number of Redis cache hits for workout data",
)

WORKOUT_CACHE_MISSES_TOTAL = Counter(
    "workout_cache_misses_total",
    "Number of Redis cache misses for workout data",
)

WORKOUT_CACHE_ERRORS_TOTAL = Counter(
    "workout_cache_errors_total",
    "Number of Redis cache errors for workout data",
)

SESSION_CACHE_HITS_TOTAL = Counter(
    "session_cache_hits_total",
    "Number of Redis cache hits for session data",
)

SESSION_CACHE_MISSES_TOTAL = Counter(
    "session_cache_misses_total",
    "Number of Redis cache misses for session data",
)

SESSION_CACHE_ERRORS_TOTAL = Counter(
    "session_cache_errors_total",
    "Number of Redis cache errors for session data",
)
