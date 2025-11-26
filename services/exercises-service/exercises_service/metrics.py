from prometheus_client import Counter

EXERCISE_DEFINITIONS_CREATED_TOTAL = Counter(
    "exercise_definitions_created_total",
    "Number of exercise definitions created via exercises-service",
)

EXERCISE_INSTANCES_CREATED_TOTAL = Counter(
    "exercise_instances_created_total",
    "Number of exercise instances created via exercises-service",
)

EXERCISE_INSTANCES_BATCH_CREATED_TOTAL = Counter(
    "exercise_instances_batch_created_total",
    "Number of exercise instances created through batch endpoint",
)

EXERCISE_SETS_UPDATED_TOTAL = Counter(
    "exercise_sets_updated_total",
    "Number of exercise sets updated via exercises-service",
)

EXERCISE_CACHE_HITS_TOTAL = Counter(
    "exercise_cache_hits_total",
    "Number of Redis cache hits in exercises-service",
)

EXERCISE_CACHE_MISSES_TOTAL = Counter(
    "exercise_cache_misses_total",
    "Number of Redis cache misses in exercises-service",
)

EXERCISE_CACHE_ERRORS_TOTAL = Counter(
    "exercise_cache_errors_total",
    "Number of Redis cache errors in exercises-service",
)
