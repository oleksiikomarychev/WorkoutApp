from prometheus_client import Counter

CRM_LINKS_CREATED_TOTAL = Counter(
    "crm_links_created_total",
    "Number of coach-athlete links created",
)

CRM_NOTES_CREATED_TOTAL = Counter(
    "crm_notes_created_total",
    "Number of coach-athlete notes created",
)

CRM_TAGS_CREATED_TOTAL = Counter(
    "crm_tags_created_total",
    "Number of coach-specific tags created",
)

CRM_TAG_ASSIGNMENTS_TOTAL = Counter(
    "crm_tag_assignments_total",
    "Number of tag assignments to coach-athlete links",
)

CRM_WORKOUT_UPDATES_TOTAL = Counter(
    "crm_workout_updates_total",
    "Number of workouts updated via CRM coach tools",
)

CRM_EXERCISE_UPDATES_TOTAL = Counter(
    "crm_exercise_updates_total",
    "Number of exercise instances updated via CRM coach tools",
)

CRM_MASS_EDIT_REQUESTS_TOTAL = Counter(
    "crm_mass_edit_requests_total",
    "Number of manual mass-edit requests executed via CRM",
)

CRM_AI_MASS_EDIT_REQUESTS_TOTAL = Counter(
    "crm_ai_mass_edit_requests_total",
    "Number of AI-driven mass-edit requests executed via CRM",
)
