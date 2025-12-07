import json
from typing import Any

import httpx
import structlog

from ..config import settings
from .llm_wrapper import generate_structured_output
from .plan_analysis import fetch_exercise_definitions_map
from .tool_agent import ToolSpec

logger = structlog.get_logger(__name__)

MACRO_GENERATION_PROMPT = """
You are an expert system for configuring "Training Macros" (automation rules).
Your task is to convert a user's natural language request into a specific JSON configuration object ("MacroRule").

### SCHEMA DEFINITION

A MacroRule consists of: Trigger, Condition, Action, Duration.

    **1. Trigger** (When to check?)
    - `metric` (enum):
      - "Readiness_Score" (User's daily readiness 0-10)
      - "e1RM" (Estimated 1 Rep Max on a specific exercise)
      - "Performance_Trend" (General trend of a specific exercise)
      - "RPE_Session" (RPE of a whole session 1-10)
      - "Total_Reps" (Total reps in a workout)
      - "RPE_Delta_From_Plan" (Actual RPE - Planned RPE)
    - `exercise_ids` (list[int]): Required if metric is e1RM,
      Performance_Trend, or Deltas. Use the EXERCISE MAP below to
      resolve names.

    **2. Condition** (Is the rule met?)
    - `op` (enum): ">", "<", ">=", "<=", "=", "in_range", "stagnates_for", "deviates_from_avg", "holds_for"
    - `value` (float): Required for comparison ops.
    - `range` (list[float]): Required for "in_range" (e.g. [0, 5]).
    - `n` (int): Required for "stagnates_for", "deviates_from_avg", "holds_for" (number of workouts).
    - `relation` (enum): ">", "<", ... Required for "holds_for" (e.g. holds_for 3 workouts where metric < value).

    **3. Action** (What to do?)
    - `type` (enum): "Adjust_Load", "Adjust_Sets", "Adjust_Reps"
    - `params` (dict):
      - For `Adjust_Load`: { "mode": "by_Percent", "value": 1.05 }
        (means +5% load). Use < 1.0 for decrease.
      - For `Adjust_Sets`: { "mode": "by_Value", "value": 1 }
        (means +1 set). Use negative for decrease.
      - For `Adjust_Reps`: { "mode": "by_Value", "value": -2 }
        (means -2 reps).
    - `target` (object, optional):
      - `exercise_ids`: [int] (List of exercises to apply changes to. If
        omitted, applies to the triggering exercise or workout).

    **4. Duration** (How long to apply?)
    - `scope`: "Next_N_Workouts"
    - `count` (int): Number of future workouts to affect.

### EXERCISE MAP (Name -> ID)
{exercise_map_json}

    ### INSTRUCTIONS
    1. Analyze the USER REQUEST.
    2. Map exercise names to IDs strictly using the EXERCISE MAP. If an
       exercise is not found, pick the closest match or ask for clarification
       (but here, try to guess).
    3. Construct the JSON.
    4. If the request is impossible to map to this schema, return a JSON with
       "error": "Reason...".

### EXAMPLES

User: "If my readiness is below 4, lower weights by 10% for the next 2 workouts."
JSON:
{
  "name": "Low Readiness Adjustment",
  "rule": {
    "trigger": { "metric": "Readiness_Score" },
    "condition": { "op": "<", "value": 4 },
    "action": { "type": "Adjust_Load", "params": { "mode": "by_Percent", "value": 0.90 } },
    "duration": { "scope": "Next_N_Workouts", "count": 2 }
  }
}

User: "If my Bench Press e1RM stagnates for 3 workouts, add 1 set to Bench Press for the next 4 sessions."
JSON:
{
  "name": "Bench Press Stagnation Breaker",
  "rule": {
    "trigger": { "metric": "e1RM", "exercise_ids": [101] },  // Assuming 101 is Bench Press
    "condition": { "op": "stagnates_for", "n": 3, "epsilon_percent": 0.01 },
    "action": {
      "type": "Adjust_Sets",
      "params": { "mode": "by_Value", "value": 1 },
      "target": { "exercise_ids": [101] }
    },
    "duration": { "scope": "Next_N_Workouts", "count": 4 }
  }
}

### CURRENT REQUEST
User: "{user_request}"
"""


async def generate_macro_payload(user_request: str, exercise_map: dict[str, int]) -> dict[str, Any]:
    map_str = json.dumps(exercise_map, indent=None)

    prompt = MACRO_GENERATION_PROMPT.format(exercise_map_json=map_str, user_request=user_request)

    response_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "rule": {"type": "object"},
            "error": {"type": "string"},
        },
        "required": ["name", "rule"],
    }

    return await generate_structured_output(prompt=prompt, response_schema=response_schema, temperature=0.1)


async def create_macro_in_backend(calendar_plan_id: int, payload: dict[str, Any], user_id: str) -> dict[str, Any]:
    url = f"{settings.plans_service_url}/plans/calendar-plans/{calendar_plan_id}/macros/"
    headers = {"X-User-Id": user_id}

    api_payload = {
        "name": payload.get("name", "New Macro"),
        "rule": payload.get("rule"),
        "is_active": True,
        "priority": 100,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, json=api_payload, headers=headers)
        if resp.status_code == 422:
            return {"error": "Validation failed", "details": resp.json()}
        resp.raise_for_status()
        return resp.json()


def create_manage_macros_tool(user_id: str) -> ToolSpec:
    parameters_schema = {
        "type": "object",
        "required": ["calendar_plan_id", "instruction"],
        "properties": {
            "calendar_plan_id": {"type": "integer", "description": "ID of the calendar plan to add the macro to"},
            "instruction": {
                "type": "string",
                "description": "The user's natural language instruction for the macro rule.",
            },
        },
    }

    async def handler(args: dict[str, Any]) -> dict[str, Any]:
        calendar_plan_id = args.get("calendar_plan_id")
        instruction = args.get("instruction")

        if not calendar_plan_id or not instruction:
            raise ValueError("calendar_plan_id and instruction are required")

        try:
            ex_def_map = await fetch_exercise_definitions_map()

            name_to_id = {d["name"]: d["id"] for d in ex_def_map.values()}
        except Exception as e:
            logger.error("failed_to_fetch_exercises", error=str(e))
            name_to_id = {}

        try:
            llm_result = await generate_macro_payload(instruction, name_to_id)
        except Exception as e:
            return {"error": f"LLM generation failed: {str(e)}"}

        if llm_result.get("error"):
            return {"error": llm_result["error"]}

        try:
            result = await create_macro_in_backend(int(calendar_plan_id), llm_result, user_id)
            return {
                "status": "success",
                "message": f"Macro '{result.get('name')}' created successfully.",
                "macro_id": result.get("id"),
                "details": result,
            }
        except Exception as e:
            logger.error("create_macro_failed", error=str(e))
            return {"error": f"Failed to create macro: {str(e)}"}

    return ToolSpec(
        name="create_manage_macros",
        description="Create a new automation macro for the plan based on natural language instructions.",
        parameters_schema=parameters_schema,
        handler=handler,
    )
