from prometheus_client import Counter

CALENDAR_PLANS_CREATED_TOTAL = Counter(
    "calendar_plans_created_total",
    "Number of calendar plans created",
)

CALENDAR_PLAN_VARIANTS_CREATED_TOTAL = Counter(
    "calendar_plan_variants_created_total",
    "Number of calendar plan variants created",
)

PLAN_MASS_EDITS_APPLIED_TOTAL = Counter(
    "plan_mass_edits_applied_total",
    "Number of plan mass-edit apply operations",
)

PLAN_WORKOUTS_GENERATED_TOTAL = Counter(
    "plan_workouts_generated_total",
    "Number of workout payloads generated from plans",
)

PLANS_CACHE_HITS_TOTAL = Counter(
    "plans_cache_hits_total",
    "Number of successful Redis cache hits in plans-service",
)

PLANS_CACHE_MISSES_TOTAL = Counter(
    "plans_cache_misses_total",
    "Number of Redis cache misses in plans-service",
)

PLANS_CACHE_ERRORS_TOTAL = Counter(
    "plans_cache_errors_total",
    "Number of Redis cache errors in plans-service",
)
