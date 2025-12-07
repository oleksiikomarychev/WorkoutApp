from prometheus_client import Counter

TRAINING_PLANS_GENERATED_TOTAL = Counter(
    "training_plans_generated_total",
    "Number of training plans generated via agent-service",
    ["variant"],
)

MASS_EDIT_COMMANDS_REQUESTED_TOTAL = Counter(
    "mass_edit_commands_requested_total",
    "Number of AI mass-edit commands requested",
)

MASS_EDIT_APPLICATIONS_TOTAL = Counter(
    "mass_edit_applications_total",
    "Number of AI mass-edit applications executed",
)

AVATARS_GENERATED_TOTAL = Counter(
    "avatars_generated_total",
    "Number of AI avatars generated",
)

AVATARS_APPLIED_TOTAL = Counter(
    "avatars_applied_total",
    "Number of avatar apply operations",
)

PLAN_ANALYSIS_REQUESTED_TOTAL = Counter(
    "plan_analysis_requested_total",
    "Number of AI plan analysis requests",
)
