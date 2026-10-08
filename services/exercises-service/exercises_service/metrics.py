from prometheus_client import Counter

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