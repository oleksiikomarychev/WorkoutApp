from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class MacroMetric(str, Enum):
    READINESS_SCORE = "Readiness_Score"
    E1RM = "e1RM"
    PERFORMANCE_TREND = "Performance_Trend"
    RPE_SESSION = "RPE_Session"
    TOTAL_REPS = "Total_Reps"
    RPE_DELTA_FROM_PLAN = "RPE_Delta_From_Plan"
    REPS_DELTA_FROM_PLAN = "Reps_Delta_From_Plan"


class MacroConditionOp(str, Enum):
    GT = ">"
    LT = "<"
    GE = ">="
    LE = "<="
    EQ = "="
    NE = "!="
    IN_RANGE = "in_range"
    NOT_IN_RANGE = "not_in_range"
    STAGNATES_FOR = "stagnates_for"
    DEVIATES_FROM_AVG = "deviates_from_avg"
    HOLDS_FOR = "holds_for"
    HOLDS_FOR_SETS = "holds_for_sets"


class MacroConditionRelation(str, Enum):
    GT = ">"
    GE = ">="
    LT = "<"
    LE = "<="
    IN_RANGE = "in_range"
    NOT_IN_RANGE = "not_in_range"


class MacroActionType(str, Enum):
    ADJUST_LOAD = "Adjust_Load"
    ADJUST_REPS = "Adjust_Reps"
    ADJUST_SETS = "Adjust_Sets"
    INJECT_MESOCYCLE = "Inject_Mesocycle"


class AdjustLoadMode(str, Enum):
    BY_PERCENT = "by_Percent"
    TO_TARGET = "to_Target"


class AdjustRepsMode(str, Enum):
    BY_VALUE = "by_Value"
    TO_TARGET = "to_Target"


class AdjustSetsMode(str, Enum):
    BY_VALUE = "by_Value"


class InjectMesocycleMode(str, Enum):
    BY_TEMPLATE = "by_Template"
    BY_EXISTING = "by_Existing"


class MacroDurationScope(str, Enum):
    NEXT_N_WORKOUTS = "Next_N_Workouts"


class MacroTargetSelectorType(str, Enum):
    TAGS = "tags"


class MacroTagSelectorValue(BaseModel):
    movement_type: Optional[List[str]] = None
    region: Optional[List[str]] = None
    muscle_group: Optional[List[str]] = None
    equipment: Optional[List[str]] = None

    @model_validator(mode="after")
    def _ensure_any_value(cls, values: "MacroTagSelectorValue") -> "MacroTagSelectorValue":
        if not any(getattr(values, attr) for attr in ("movement_type", "region", "muscle_group", "equipment")):
            raise ValueError("selector.value must contain at least one non-empty filter")
        return values


class MacroTargetSelector(BaseModel):
    type: MacroTargetSelectorType
    value: MacroTagSelectorValue


class MacroActionTarget(BaseModel):
    exercise_id: Optional[int] = Field(None, ge=1)
    exercise_ids: Optional[List[int]] = Field(None, min_length=1)
    selector: Optional[MacroTargetSelector] = None

    @model_validator(mode="after")
    def _normalize_ids(cls, values: "MacroActionTarget") -> "MacroActionTarget":
        ids = values.exercise_ids
        if ids:
            deduped = []
            seen: set[int] = set()
            for val in ids:
                if val is None:
                    continue
                if val < 1:
                    raise ValueError("exercise_ids must contain positive integers")
                if val not in seen:
                    seen.add(val)
                    deduped.append(val)
            if not deduped:
                raise ValueError("exercise_ids must contain at least one valid id")
            values.exercise_ids = deduped
        if values.exercise_id is not None and values.exercise_id < 1:
            raise ValueError("exercise_id must be a positive integer")
        return values


class MacroTrigger(BaseModel):
    metric: MacroMetric
    exercise_id: Optional[int] = Field(None, ge=1)
    exercise_ids: Optional[List[int]] = Field(None, min_length=1)
    selector: Optional[MacroTargetSelector] = None

    @model_validator(mode="after")
    def _normalize_ids(cls, values: "MacroTrigger") -> "MacroTrigger":
        if values.exercise_ids:
            deduped: List[int] = []
            seen: set[int] = set()
            for val in values.exercise_ids:
                if val is None:
                    continue
                if val < 1:
                    raise ValueError("exercise_ids must contain positive integers")
                if val not in seen:
                    seen.add(val)
                    deduped.append(val)
            if not deduped:
                raise ValueError("exercise_ids must contain at least one valid id")
            values.exercise_ids = deduped
        if values.exercise_id is not None and values.exercise_id < 1:
            raise ValueError("exercise_id must be a positive integer")
        return values


class MacroCondition(BaseModel):
    op: MacroConditionOp
    value: Optional[float] = None
    range: Optional[List[float]] = Field(None, min_length=2, max_length=2)
    relation: Optional[MacroConditionRelation] = None
    n: Optional[int] = Field(None, ge=1)
    n_sets: Optional[int] = Field(None, ge=1)
    epsilon_percent: Optional[float] = Field(None, ge=0)
    value_percent: Optional[float] = Field(None, ge=0)
    direction: Optional[str] = Field(None, pattern="^(positive|negative)?$")

    @model_validator(mode="after")
    def _validate_payload(cls, values: "MacroCondition") -> "MacroCondition":
        op = values.op

        if (
            op
            in {
                MacroConditionOp.GT,
                MacroConditionOp.LT,
                MacroConditionOp.GE,
                MacroConditionOp.LE,
                MacroConditionOp.EQ,
                MacroConditionOp.NE,
            }
            and values.value is None
        ):
            raise ValueError("condition.value is required for comparison operators")
        if op in {MacroConditionOp.IN_RANGE, MacroConditionOp.NOT_IN_RANGE}:
            if values.range is None:
                raise ValueError("condition.range is required for range operators")
            lo, hi = values.range
            if lo is None or hi is None:
                raise ValueError("condition.range must contain numeric bounds")
        if op == MacroConditionOp.STAGNATES_FOR:
            if values.n is None:
                raise ValueError("condition.n is required for stagnates_for")
            if values.epsilon_percent is None:
                raise ValueError("condition.epsilon_percent is required for stagnates_for")
        if op == MacroConditionOp.DEVIATES_FROM_AVG:
            if values.n is None:
                raise ValueError("condition.n is required for deviates_from_avg")
            if values.value_percent is None:
                raise ValueError("condition.value_percent is required for deviates_from_avg")
        if op == MacroConditionOp.HOLDS_FOR:
            if values.n is None:
                raise ValueError("condition.n is required for holds_for")
            if values.relation is None:
                raise ValueError("condition.relation is required for holds_for")
            relation = values.relation
            if relation in {MacroConditionRelation.IN_RANGE, MacroConditionRelation.NOT_IN_RANGE}:
                if values.range is None:
                    raise ValueError("condition.range is required for holds_for when relation is range-based")
            else:
                if values.value is None:
                    raise ValueError("condition.value is required for holds_for")
        if op == MacroConditionOp.HOLDS_FOR_SETS:
            if values.n_sets is None:
                raise ValueError("condition.n_sets is required for holds_for_sets")
            if values.relation is None:
                raise ValueError("condition.relation is required for holds_for_sets")
            if values.value is None:
                raise ValueError("condition.value is required for holds_for_sets")
        return values


class MacroDuration(BaseModel):
    scope: MacroDurationScope = MacroDurationScope.NEXT_N_WORKOUTS
    count: int = Field(1, ge=1, le=100)


class MacroAction(BaseModel):
    type: MacroActionType
    params: Dict[str, Any] = Field(default_factory=dict)
    target: Optional[MacroActionTarget] = None

    @model_validator(mode="after")
    def _validate_params(cls, values: "MacroAction") -> "MacroAction":
        action_type = values.type
        params = values.params or {}

        def require_keys(required: List[str]) -> None:
            missing = [k for k in required if params.get(k) is None]
            if missing:
                raise ValueError(f"action.params missing required fields: {', '.join(missing)}")

        if action_type == MacroActionType.ADJUST_LOAD:
            mode = params.get("mode")
            if mode not in {m.value for m in AdjustLoadMode}:
                raise ValueError("Adjust_Load params.mode must be 'by_Percent' or 'to_Target'")
            if mode == AdjustLoadMode.BY_PERCENT.value:
                require_keys(["value"])
            if mode == AdjustLoadMode.TO_TARGET.value:
                require_keys(["value"])
                cls._ensure_rpc_available("Adjust_Load", "to_Target")

        elif action_type == MacroActionType.ADJUST_REPS:
            mode = params.get("mode")
            if mode not in {m.value for m in AdjustRepsMode}:
                raise ValueError("Adjust_Reps params.mode must be 'by_Value' or 'to_Target'")
            if mode == AdjustRepsMode.BY_VALUE.value:
                require_keys(["value"])
            if mode == AdjustRepsMode.TO_TARGET.value:
                require_keys(["value"])
                cls._ensure_rpc_available("Adjust_Reps", "to_Target")

        elif action_type == MacroActionType.ADJUST_SETS:
            mode = params.get("mode")
            if mode != AdjustSetsMode.BY_VALUE.value:
                raise ValueError("Adjust_Sets params.mode must be 'by_Value'")
            require_keys(["value"])

        elif action_type == MacroActionType.INJECT_MESOCYCLE:
            mode = params.get("mode")
            if mode not in {m.value for m in InjectMesocycleMode}:
                raise ValueError("Inject_Mesocycle params.mode must be 'by_Template' or 'by_Existing'")
            placement = params.get("placement")
            if placement is not None and not isinstance(placement, dict):
                raise ValueError("Inject_Mesocycle params.placement must be an object")
            if mode == InjectMesocycleMode.BY_TEMPLATE.value and params.get("template_id") is None:
                raise ValueError("Inject_Mesocycle by_Template requires template_id")
            if mode == InjectMesocycleMode.BY_EXISTING.value and not any(
                params.get(key) is not None for key in ("source_mesocycle_id", "mesocycle_id")
            ):
                raise ValueError("Inject_Mesocycle by_Existing requires source_mesocycle_id or mesocycle_id")

        return values

    @staticmethod
    def _ensure_rpc_available(action: str, mode: str) -> None:
        try:
            from ..services.macro_engine import rpc_get_intensity, rpc_get_volume
        except Exception:  # pragma: no cover - import issue
            rpc_get_intensity = None
            rpc_get_volume = None

        if action == "Adjust_Load" and mode == "to_Target" and rpc_get_intensity is None:
            raise ValueError("Adjust_Load to_Target requires RPE RPC get_intensity")
        if action == "Adjust_Reps" and mode == "to_Target" and rpc_get_volume is None:
            raise ValueError("Adjust_Reps to_Target requires RPE RPC get_volume")


class MacroRule(BaseModel):
    trigger: MacroTrigger
    condition: MacroCondition
    action: MacroAction
    duration: MacroDuration = Field(default_factory=MacroDuration)

    @model_validator(mode="after")
    def _validate_semantics(cls, values: "MacroRule") -> "MacroRule":
        metric = values.trigger.metric
        op = values.condition.op

        allowed_ops: Dict[MacroMetric, set[MacroConditionOp]] = {
            MacroMetric.E1RM: {
                MacroConditionOp.GT,
                MacroConditionOp.GE,
                MacroConditionOp.LT,
                MacroConditionOp.LE,
                MacroConditionOp.EQ,
                MacroConditionOp.NE,
                MacroConditionOp.IN_RANGE,
                MacroConditionOp.NOT_IN_RANGE,
            },
            MacroMetric.PERFORMANCE_TREND: {
                MacroConditionOp.STAGNATES_FOR,
                MacroConditionOp.DEVIATES_FROM_AVG,
            },
            MacroMetric.READINESS_SCORE: {
                MacroConditionOp.GT,
                MacroConditionOp.GE,
                MacroConditionOp.LT,
                MacroConditionOp.LE,
                MacroConditionOp.EQ,
                MacroConditionOp.NE,
                MacroConditionOp.IN_RANGE,
                MacroConditionOp.NOT_IN_RANGE,
                MacroConditionOp.HOLDS_FOR,
            },
            MacroMetric.RPE_SESSION: {
                MacroConditionOp.GT,
                MacroConditionOp.GE,
                MacroConditionOp.LT,
                MacroConditionOp.LE,
                MacroConditionOp.EQ,
                MacroConditionOp.NE,
                MacroConditionOp.IN_RANGE,
                MacroConditionOp.NOT_IN_RANGE,
                MacroConditionOp.HOLDS_FOR,
            },
            MacroMetric.TOTAL_REPS: {
                MacroConditionOp.GT,
                MacroConditionOp.GE,
                MacroConditionOp.LT,
                MacroConditionOp.LE,
                MacroConditionOp.EQ,
                MacroConditionOp.NE,
                MacroConditionOp.IN_RANGE,
                MacroConditionOp.NOT_IN_RANGE,
                MacroConditionOp.HOLDS_FOR,
            },
            MacroMetric.RPE_DELTA_FROM_PLAN: {
                MacroConditionOp.GT,
                MacroConditionOp.GE,
                MacroConditionOp.LT,
                MacroConditionOp.LE,
                MacroConditionOp.EQ,
                MacroConditionOp.NE,
                MacroConditionOp.HOLDS_FOR,
                MacroConditionOp.HOLDS_FOR_SETS,
            },
            MacroMetric.REPS_DELTA_FROM_PLAN: {
                MacroConditionOp.GT,
                MacroConditionOp.GE,
                MacroConditionOp.LT,
                MacroConditionOp.LE,
                MacroConditionOp.EQ,
                MacroConditionOp.NE,
                MacroConditionOp.HOLDS_FOR,
                MacroConditionOp.HOLDS_FOR_SETS,
            },
        }

        if metric not in allowed_ops or op not in allowed_ops[metric]:
            raise ValueError(f"condition.op '{op.value}' is not supported for metric '{metric.value}'")

        if metric == MacroMetric.READINESS_SCORE:
            cond = values.condition

            if op in {
                MacroConditionOp.GT,
                MacroConditionOp.GE,
                MacroConditionOp.LT,
                MacroConditionOp.LE,
                MacroConditionOp.EQ,
                MacroConditionOp.NE,
            }:
                if cond.value is None:
                    raise ValueError("Readiness_Score comparisons require condition.value (0-10)")
            if op in {MacroConditionOp.IN_RANGE, MacroConditionOp.NOT_IN_RANGE}:
                if cond.range is None:
                    raise ValueError("Readiness_Score range operators require condition.range [min, max]")

            # normalize to floats
            if cond.value is not None:
                cond.value = float(cond.value)
                if cond.value < 0 or cond.value > 10:
                    raise ValueError("Readiness_Score value must be between 0 and 10")
            if cond.range is not None:
                if len(cond.range) != 2:
                    raise ValueError("Readiness_Score range must contain two bounds")
                lo, hi = cond.range
                if lo is None or hi is None:
                    raise ValueError("Readiness_Score range bounds must be numeric")
                lo_f = float(lo)
                hi_f = float(hi)
                if lo_f < 0 or hi_f > 10:
                    raise ValueError("Readiness_Score range must be within 0-10")
                cond.range = [lo_f, hi_f]

        if metric in {
            MacroMetric.RPE_DELTA_FROM_PLAN,
            MacroMetric.REPS_DELTA_FROM_PLAN,
        }:
            if not (values.trigger.exercise_id or values.trigger.exercise_ids):
                raise ValueError("Delta metrics require exercise_id or exercise_ids in trigger")

        if metric in {MacroMetric.E1RM, MacroMetric.PERFORMANCE_TREND}:
            if not (values.trigger.exercise_id or values.trigger.exercise_ids):
                raise ValueError("e1RM and Performance_Trend require exercise_id or exercise_ids in trigger")

        if metric == MacroMetric.TOTAL_REPS and values.condition.op == MacroConditionOp.HOLDS_FOR:
            if values.condition.n is None:
                raise ValueError("Total_Reps holds_for requires condition.n")

        return values


class PlanMacroBase(BaseModel):
    name: str = Field(..., max_length=255)
    is_active: bool = True
    priority: int = Field(default=100, ge=0, le=10000)
    rule: MacroRule = Field(..., description="Macro rule JSON (structured DSL)")

    class Config:
        from_attributes = True


class PlanMacroCreate(PlanMacroBase):
    pass


class PlanMacroUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0, le=10000)
    rule: Optional[MacroRule] = None


class PlanMacroResponse(PlanMacroBase):
    id: int
    calendar_plan_id: int
    created_at: datetime
    updated_at: datetime
