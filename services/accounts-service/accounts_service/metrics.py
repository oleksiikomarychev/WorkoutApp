from prometheus_client import Counter

PROFILES_UPDATED_TOTAL = Counter(
    "profiles_updated_total",
    "Number of user profile updates via accounts-service",
)

COACHING_PROFILES_UPDATED_TOTAL = Counter(
    "coaching_profiles_updated_total",
    "Number of coaching profile updates via accounts-service",
)

SETTINGS_UPDATED_TOTAL = Counter(
    "settings_updated_total",
    "Number of user settings updates via accounts-service",
)

AVATARS_APPLIED_TOTAL = Counter(
    "avatars_applied_total",
    "Number of avatar apply operations via accounts-service",
)
