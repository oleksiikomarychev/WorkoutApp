"""Prometheus metrics for agent-service."""

from __future__ import annotations

from prometheus_client import REGISTRY, Counter


def _get_or_create_counter(name: str, documentation: str, labelnames: tuple[str, ...] = ()) -> Counter:
    existing = REGISTRY._names_to_collectors.get(name) or REGISTRY._names_to_collectors.get(f"{name}_total")
    if existing:
        return existing  # type: ignore[return-value]
    clean_name = name[:-6] if name.endswith("_total") else name
    existing = REGISTRY._names_to_collectors.get(clean_name)
    if existing:
        return existing  # type: ignore[return-value]
    try:
        return Counter(name, documentation, labelnames=labelnames)
    except ValueError:
        return REGISTRY._names_to_collectors.get(name) or REGISTRY._names_to_collectors.get(clean_name)  # type: ignore[return-value]


TRAINING_PLANS_GENERATED_TOTAL = _get_or_create_counter(
    "training_plans_generated_total",
    "Number of training plans generated via agent-service",
    labelnames=("variant",),
)

MASS_EDIT_COMMANDS_REQUESTED_TOTAL = _get_or_create_counter(
    "mass_edit_commands_requested_total",
    "Number of AI mass-edit commands requested",
)

MASS_EDIT_APPLICATIONS_TOTAL = _get_or_create_counter(
    "mass_edit_applications_total",
    "Number of AI mass-edit applications executed",
)

AVATARS_GENERATED_TOTAL = _get_or_create_counter(
    "avatars_generated_total",
    "Number of AI avatars generated",
)

AVATARS_APPLIED_TOTAL = _get_or_create_counter(
    "avatars_applied_total",
    "Number of avatar apply operations",
)

PLAN_ANALYSIS_REQUESTED_TOTAL = _get_or_create_counter(
    "plan_analysis_requested_total",
    "Number of AI plan analysis requests",
)
