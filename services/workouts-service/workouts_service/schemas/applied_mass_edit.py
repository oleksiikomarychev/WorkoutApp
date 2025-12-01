from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AppliedPlanExerciseFilter(BaseModel):
    """Filter describing which workouts/exercises/sets should be edited."""

    plan_order_indices: list[int] | None = Field(default=None, description="Exact plan order indices to target")
    from_order_index: int | None = Field(
        default=None,
        ge=0,
        description="Lower bound (inclusive) for plan order index",
    )
    to_order_index: int | None = Field(
        default=None,
        ge=0,
        description="Upper bound (inclusive) for plan order index",
    )
    only_future: bool = Field(
        default=True,
        description="If true, skip workouts with scheduled_for earlier than now",
    )
    scheduled_from: datetime | None = Field(
        default=None,
        description="Select workouts scheduled on/after this timestamp",
    )
    scheduled_to: datetime | None = Field(
        default=None,
        description="Select workouts scheduled on/before this timestamp",
    )
    status_in: list[str] | None = Field(
        default=None,
        description="Restrict workouts by status (e.g. pending, in_progress)",
    )
    exercise_definition_ids: list[int] | None = Field(
        default=None,
        description="Target only exercises with these definition IDs",
    )

    # Set-level filters
    intensity_lte: float | None = Field(default=None, description="Match sets with intensity <= value")
    intensity_gte: float | None = Field(default=None, description="Match sets with intensity >= value")
    volume_lte: int | None = Field(default=None, description="Match sets with reps/volume <= value")
    volume_gte: int | None = Field(default=None, description="Match sets with reps/volume >= value")
    weight_lte: float | None = Field(default=None, description="Match sets with weight <= value")
    weight_gte: float | None = Field(default=None, description="Match sets with weight >= value")
    effort_lte: float | None = Field(default=None, description="Match sets with effort/RPE <= value")
    effort_gte: float | None = Field(default=None, description="Match sets with effort/RPE >= value")

    @model_validator(mode="after")
    def validate_indexes(cls, values: "AppliedPlanExerciseFilter") -> "AppliedPlanExerciseFilter":
        if (
            values.plan_order_indices is None
            and values.from_order_index is None
            and values.to_order_index is None
            and values.scheduled_from is None
            and values.scheduled_to is None
        ):
            # At least some scope must be provided to avoid editing every workout in plan accidentally.
            raise ValueError(
                "AppliedPlanExerciseFilter must define plan_order_indices or an order/date range to scope edits"
            )
        return values


class AppliedAddExerciseSet(BaseModel):
    """Definition of a single set for a newly added exercise instance."""

    volume: int | None = Field(default=None, ge=1, description="Reps/volume for the new set")
    intensity: float | None = Field(default=None, description="Intensity (%% of 1RM) for the new set")
    weight: float | None = Field(default=None, ge=0, description="Working weight in kg for the new set")
    effort: float | None = Field(default=None, description="Effort/RPE for the new set")


class AppliedAddExerciseInstance(BaseModel):
    """Specification of a new exercise instance to create in matched workouts."""

    exercise_definition_id: int = Field(..., ge=1, description="Exercise definition (exercise_list) id to add")
    notes: str | None = Field(default=None, description="Optional notes for the new exercise instance")
    order: int | None = Field(default=None, ge=0, description="Optional order index within the workout")
    sets: list[AppliedAddExerciseSet] = Field(
        default_factory=list,
        description=(
            "Sets to create for the new exercise instance; when empty, the backend MAY apply a "
            "service-specific default pattern."
        ),
    )


class AppliedPlanExerciseActions(BaseModel):
    """Operations applied to each matched set."""

    model_config = ConfigDict(extra="forbid")

    set_intensity: float | None = Field(default=None, description="Override intensity value")
    increase_intensity_by: float | None = Field(default=None, description="Add delta to intensity")
    decrease_intensity_by: float | None = Field(default=None, description="Subtract delta from intensity")

    set_volume: int | None = Field(default=None, description="Override reps/volume")
    increase_volume_by: int | None = Field(default=None, description="Add delta to reps/volume")
    decrease_volume_by: int | None = Field(default=None, description="Subtract delta from reps/volume")

    set_weight: float | None = Field(default=None, description="Override working weight")
    increase_weight_by: float | None = Field(default=None, description="Add delta to weight (kg)")
    decrease_weight_by: float | None = Field(default=None, description="Subtract delta from weight (kg)")

    set_effort: float | None = Field(default=None, description="Override effort/RPE")
    increase_effort_by: float | None = Field(default=None, description="Add delta to effort/RPE")
    decrease_effort_by: float | None = Field(default=None, description="Subtract delta from effort/RPE")

    clamp_non_negative: bool = Field(default=True, description="Prevent volume/weight from dropping below zero")

    # Exercise-level replacement (applied plan)
    replace_exercise_definition_id_to: int | None = Field(
        default=None,
        ge=1,
        description="When set, matched exercise instances switch to this exercise definition id",
    )
    replace_exercise_name_to: str | None = Field(
        default=None,
        description="Optional human-readable exercise name to store for transparency",
    )

    # High-level operations that can create new exercise instances in matched workouts
    add_exercise_instances: list[AppliedAddExerciseInstance] | None = Field(
        default=None,
        description=(
            "Create new exercise instances with the given definition ids and sets "
            "in workouts selected by the filter."
        ),
    )

    @model_validator(mode="after")
    def validate_actions(cls, values: "AppliedPlanExerciseActions") -> "AppliedPlanExerciseActions":
        # Ensure at least one action is provided
        has_action = any(
            getattr(values, field) is not None
            for field in (
                "set_intensity",
                "increase_intensity_by",
                "decrease_intensity_by",
                "set_volume",
                "increase_volume_by",
                "decrease_volume_by",
                "set_weight",
                "increase_weight_by",
                "decrease_weight_by",
                "set_effort",
                "increase_effort_by",
                "decrease_effort_by",
                "replace_exercise_definition_id_to",
                "replace_exercise_name_to",
                "add_exercise_instances",
            )
        )
        if not has_action:
            raise ValueError("AppliedPlanExerciseActions must define at least one action")
        return values


class AppliedPlanMassEditCommand(BaseModel):
    mode: Literal["preview", "apply"] = Field(default="preview")
    filter: AppliedPlanExerciseFilter
    actions: AppliedPlanExerciseActions


class AppliedPlanMassEditResult(BaseModel):
    """Summary returned to clients after mass edit execution."""

    mode: Literal["preview", "apply"]
    workouts_matched: int
    instances_matched: int
    sets_matched: int
    sets_modified: int
    details: list[dict] = Field(
        default_factory=list,
        description="Optional per-workout change summary (best effort)",
    )


class AppliedPlanScheduleShiftCommand(BaseModel):
    """Command to shift or restructure scheduled_for dates for workouts in an applied plan.

    Supports two modes via action_type:
    - "shift": Shift all matched workouts by `days` (can be negative).
    - "set_rest": restructuring the schedule so that the gap between consecutive matched workouts
      becomes `new_rest_days`.
    """

    from_date: datetime = Field(
        ...,
        description="Start date (inclusive) from which workouts should be shifted/restructured",
    )
    to_date: datetime | None = Field(
        default=None,
        description="End date (inclusive) until which workouts should be shifted/restructured",
    )
    days: int = Field(
        default=0,
        description="Number of days to shift scheduled_for by (used when action_type='shift')",
    )
    new_rest_days: int | None = Field(
        default=None,
        description="New gap in days between consecutive workouts (used when action_type='set_rest')",
    )
    action_type: Literal["shift", "set_rest"] = Field(
        default="shift",
        description="Type of schedule manipulation to perform",
    )
    add_rest_every_n_workouts: int | None = Field(
        default=None,
        ge=1,
        description="Insert extra rest days after every N workouts (cyclic pattern)",
    )
    add_rest_at_indices: list[int] | None = Field(
        default=None,
        description="List of workout indices (relative to the selection) after which to insert extra rest days",
    )
    add_rest_days_amount: int = Field(
        default=1,
        ge=1,
        description="How many rest days to insert when a pattern matches (default: 1)",
    )
    only_future: bool = Field(
        default=True,
        description="If true, skip workouts with scheduled_for earlier than now",
    )
    status_in: list[str] | None = Field(
        default=None,
        description=(
            "Optional whitelist of workout statuses to shift (e.g. pending, in_progress); "
            "when omitted, completed workouts are always skipped."
        ),
    )

    mode: Literal["preview", "apply"] | None = Field(
        default=None,
        description=(
            "Execution mode: 'preview' to compute the effect without persisting changes, "
            "or 'apply' to commit schedule changes. When omitted, defaults to 'apply' "
            "for backwards compatibility."
        ),
    )
