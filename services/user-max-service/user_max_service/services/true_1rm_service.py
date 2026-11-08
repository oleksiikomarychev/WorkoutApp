"""Service for calculating true 1RM based on maximum weight and repetitions."""

from typing import Any


def calculate_true_1rm(user_max: Any) -> float:
    """Calculate true 1RM for a user max record using explicit value or Epley formula.

    Formula: 1RM = weight * (1 + reps / 30.0) when reps > 0.
    """
    if user_max is None:
        return 0.0

    true_1rm = (
        user_max.get("true_1rm")
        if isinstance(user_max, dict)
        else getattr(user_max, "true_1rm", None)
    )
    if true_1rm is not None:
        try:
            return float(true_1rm)
        except (TypeError, ValueError):
            pass

    max_weight = (
        user_max.get("max_weight")
        if isinstance(user_max, dict)
        else getattr(user_max, "max_weight", 0.0)
    )
    rep_max = (
        user_max.get("rep_max")
        if isinstance(user_max, dict)
        else getattr(user_max, "rep_max", None)
    )

    try:
        weight = float(max_weight or 0.0)
    except (TypeError, ValueError):
        return 0.0

    if rep_max is not None and rep_max > 0:
        try:
            return float(weight * (1.0 + float(rep_max) / 30.0))
        except (TypeError, ValueError):
            pass

    return weight
