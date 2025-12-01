from typing import Any, Dict, List, Optional

import httpx
import structlog

from ..config import settings
from ..metrics import PLAN_ANALYSIS_REQUESTED_TOTAL  # We might want a new metric for analysis
from ..prompts.plan_analysis import ANALYSIS_PROMPT_TEMPLATE, TEMPLATE_ANALYSIS_PROMPT
from .llm_wrapper import generate_structured_output
from .tool_agent import ToolSpec

logger = structlog.get_logger(__name__)

ANALYSIS_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["summary", "recommendations"],
    "properties": {
        "summary": {
            "type": "string",
            "description": "A detailed analysis of the user's progress, consistency, and trends.",
        },
        "recommendations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of specific actionable recommendations or warnings.",
        },
        "sentiment": {
            "type": "string",
            "enum": ["positive", "neutral", "negative", "warning"],
            "description": "Overall assessment of the progress.",
        },
    },
}


async def fetch_applied_plan_details(applied_plan_id: int, user_id: str) -> Dict[str, Any]:
    url = f"{settings.plans_service_url}/plans/applied-plans/{applied_plan_id}"
    headers = {"X-User-Id": user_id}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code == 404:
            raise ValueError(f"Applied plan {applied_plan_id} not found")
        resp.raise_for_status()
        return resp.json()


async def fetch_calendar_plan_details(calendar_plan_id: int, user_id: str) -> Dict[str, Any]:
    """Fetch calendar plan (template) details."""
    url = f"{settings.plans_service_url}/plans/calendar-plans/{calendar_plan_id}"
    headers = {"X-User-Id": user_id}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code == 404:
            raise ValueError(f"Calendar plan {calendar_plan_id} not found")
        resp.raise_for_status()
        return resp.json()


async def fetch_plan_workouts_with_details(applied_plan_id: int, user_id: str) -> List[Dict[str, Any]]:
    """Fetch lightweight workout details including exercise IDs."""
    url = f"{settings.workouts_service_url}/workouts/applied-plans/{applied_plan_id}/details"
    headers = {"X-User-Id": user_id}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()


async def fetch_exercise_definitions_map() -> Dict[int, Dict[str, Any]]:
    """Fetch all exercise definitions and return a map {id: details}."""
    url = f"{settings.exercises_service_url}/exercises/definitions/"
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        items = resp.json()
        return {item["id"]: item for item in items}


async def fetch_plan_analytics(applied_plan_id: int, user_id: str) -> Dict[str, Any]:
    url = f"{settings.workouts_service_url}/workouts/analytics/in-plan"
    params = {"applied_plan_id": applied_plan_id, "group_by": "order"}
    headers = {"X-User-Id": user_id}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        return resp.json()


def extract_workouts_from_calendar_plan(plan_data: Dict[str, Any]) -> tuple[List[Dict[str, Any]], str]:
    """Flatten the nested structure of a calendar plan into workouts AND build a structure summary.

    Returns
    -------
    (workouts, structure_summary_text)

    In addition to basic workout metadata, this helper also pre-computes
    simple load metrics derived from the nested sets under exercises:

    - exercise_ids: list of unique exercise_definition_id values in workout
    - total_sets: total number of sets in the workout
    - total_volume: sum of set "volume" values (if present)
    - avg_intensity: average of non-null set "intensity" values
    - avg_effort: average of non-null set "effort" values
    """
    workouts: List[Dict[str, Any]] = []
    structure_lines: List[str] = []

    mesocycles = plan_data.get("mesocycles", [])
    for meso in mesocycles:
        meso_name = meso.get("name", "Unnamed Meso")
        microcycles = meso.get("microcycles", [])

        # Calculate duration from microcycles (more reliable than user input)
        total_days = sum(m.get("days_count", 0) or 0 for m in microcycles)
        calculated_weeks = round(total_days / 7, 1) if total_days else 0

        duration_display = f"{total_days} days (~{calculated_weeks} weeks)"
        structure_lines.append(f"Mesocycle: {meso_name} ({duration_display})")

        meso_total_sets = 0
        meso_total_volume = 0
        meso_intensities: List[float] = []
        meso_efforts: List[float] = []

        for micro in microcycles:
            micro_name = micro.get("name", "Microcycle")
            days_count = micro.get("days_count", "?")

            micro_total_sets = 0
            micro_total_volume = 0
            micro_intensities: List[float] = []
            micro_efforts: List[float] = []

            for workout in micro.get("plan_workouts", []):
                # Enrich with structural context
                w_copy = workout.copy()
                w_copy["meso_name"] = meso_name
                w_copy["micro_order"] = micro.get("order")

                ex_ids: List[int] = []
                total_sets = 0
                total_volume = 0
                intensity_vals: List[float] = []
                effort_vals: List[float] = []

                for pe in workout.get("exercises", []) or []:
                    exercise_def_id = pe.get("exercise_definition_id")
                    if isinstance(exercise_def_id, int):
                        ex_ids.append(exercise_def_id)

                    for s in pe.get("sets", []) or []:
                        total_sets += 1
                        micro_total_sets += 1
                        meso_total_sets += 1

                        volume = s.get("volume")
                        if isinstance(volume, (int, float)):
                            total_volume += volume
                            micro_total_volume += volume
                            meso_total_volume += volume

                        intensity = s.get("intensity")
                        if isinstance(intensity, (int, float)):
                            iv = float(intensity)
                            intensity_vals.append(iv)
                            micro_intensities.append(iv)
                            meso_intensities.append(iv)

                        effort = s.get("effort")
                        if isinstance(effort, (int, float)):
                            ev = float(effort)
                            effort_vals.append(ev)
                            micro_efforts.append(ev)
                            meso_efforts.append(ev)

                w_copy["exercise_ids"] = ex_ids
                w_copy["total_sets"] = total_sets
                w_copy["total_volume"] = total_volume
                if intensity_vals:
                    w_copy["avg_intensity"] = sum(intensity_vals) / len(intensity_vals)
                if effort_vals:
                    w_copy["avg_effort"] = sum(effort_vals) / len(effort_vals)

                workouts.append(w_copy)

            # After all workouts in microcycle, summarize its load
            if micro_total_sets:
                avg_micro_intensity = sum(micro_intensities) / len(micro_intensities) if micro_intensities else 0.0
                avg_micro_effort = sum(micro_efforts) / len(micro_efforts) if micro_efforts else 0.0
                structure_lines.append(
                    f"  - Microcycle: {micro_name} ({days_count} days) | "
                    f"Sets: {micro_total_sets}, Approx. volume: {micro_total_volume}, "
                    f"Avg intensity: {avg_micro_intensity:.1f}, Avg effort (RPE): {avg_micro_effort:.1f}"
                )
            else:
                structure_lines.append(f"  - Microcycle: {micro_name} ({days_count} days)")

        # After all microcycles in mesocycle, summarize its load
        if meso_total_sets:
            avg_meso_intensity = sum(meso_intensities) / len(meso_intensities) if meso_intensities else 0.0
            avg_meso_effort = sum(meso_efforts) / len(meso_efforts) if meso_efforts else 0.0
            structure_lines.append(
                f"    Mesocycle totals → Sets: {meso_total_sets}, "
                f"Approx. volume: {meso_total_volume}, Avg intensity: {avg_meso_intensity:.1f}, "
                f"Avg effort (RPE): {avg_meso_effort:.1f}"
            )

    return workouts, "\n".join(structure_lines)


async def generate_plan_analysis(
    user_id: str, applied_plan_id: Optional[int] = None, calendar_plan_id: Optional[int] = None, user_focus: str = ""
) -> Dict[str, Any]:
    if not applied_plan_id and not calendar_plan_id:
        raise ValueError("Either applied_plan_id or calendar_plan_id must be provided")

    # 1. Gather Data
    try:
        exercise_defs = await fetch_exercise_definitions_map()

        plan_name = "Unknown Plan"
        workouts = []
        history_context = "No execution history (Template View)"
        analytics_context = "No execution analytics (Template View)"
        context_str = ""

        if applied_plan_id:
            # Fetch applied plan data
            plan_details = await fetch_applied_plan_details(applied_plan_id, user_id)
            workouts = await fetch_plan_workouts_with_details(applied_plan_id, user_id)
            analytics = await fetch_plan_analytics(applied_plan_id, user_id)

            plan_name = plan_details.get("plan_name", "Unknown Plan")
            start_date = plan_details.get("start_date")
            end_date = plan_details.get("end_date")

            # Workouts Summary
            total_workouts = len(workouts)
            completed = sum(1 for w in workouts if w.get("status") == "completed")
            skipped = sum(1 for w in workouts if w.get("status") == "skipped")

            context_str = (
                f"Plan: {plan_name}\n"
                f"Period: {start_date} to {end_date}\n"
                f"Progress: {completed}/{total_workouts} completed ({skipped} skipped)"
            )

            # Recent history
            sorted_workouts = sorted(workouts, key=lambda x: x.get("scheduled_for") or "")
            history_lines = []
            for w in sorted_workouts:
                status = w.get("status")
                date = w.get("scheduled_for", "")[:10]
                name = w.get("name", "Workout")
                if status in ["completed", "skipped"]:
                    history_lines.append(f"- {date}: {name} [{status.upper()}]")

            if len(history_lines) > 20:
                history_context = "\n".join(history_lines[-20:])
            else:
                history_context = "\n".join(history_lines) or "No completed workouts yet."

            # Analytics Summary
            items = analytics.get("items", [])
            vol_trend = []
            int_trend = []
            for item in items:
                m = item.get("metrics", {})
                vol_trend.append(m.get("volume_sum", 0))
                int_trend.append(m.get("intensity_avg", 0))

            analytics_context = f"""
            Total Volume Trend (last 5): {vol_trend[-5:]}
            Intensity Trend (last 5): {int_trend[-5:]}
            """

        elif calendar_plan_id:
            # Fetch calendar plan (template) data
            plan_details = await fetch_calendar_plan_details(calendar_plan_id, user_id)
            plan_name = plan_details.get("name", "Unknown Plan")
            duration = plan_details.get("duration_weeks", "?")

            # Flatten nested structure and compute set-level aggregates
            workouts, structure_summary = extract_workouts_from_calendar_plan(plan_details)

            total_workouts = len(workouts)
            total_sets = sum(w.get("total_sets", 0) for w in workouts)
            total_volume = sum(w.get("total_volume", 0) for w in workouts)
            avg_sets_per_workout = total_sets / total_workouts if total_workouts else 0.0

            # Collect average intensity and effort (RPE) across workouts (if present)
            all_intensities = [w["avg_intensity"] for w in workouts if "avg_intensity" in w]
            avg_plan_intensity = sum(all_intensities) / len(all_intensities) if all_intensities else 0.0

            all_efforts = [w["avg_effort"] for w in workouts if "avg_effort" in w]
            avg_plan_effort = sum(all_efforts) / len(all_efforts) if all_efforts else 0.0

            context_lines = [
                f"Plan Template: {plan_name}",
                f"Duration: {duration} weeks",
                f"Total Workouts: {total_workouts}",
                "Plan Structure Summary:",
                structure_summary,
                "",
                "Workload Metrics:",
                f"- Total Sets: {total_sets}",
                f"- Avg Sets per Workout: {avg_sets_per_workout:.1f}",
                f"- Approx. Total Volume (sum of set volume): {total_volume}",
                f"- Avg Intensity (across workouts): {avg_plan_intensity:.1f}",
                f"- Avg Effort (RPE, across workouts): {avg_plan_effort:.1f}",
            ]

            context_str = "\n".join(context_lines)
            history_context = (
                "This is a plan template. Analyze the structure, split, periodization, "
                "and approximate workload based on sets."
            )
            analytics_context = "N/A (Template)"

    except Exception as exc:
        logger.error("plan_analysis_data_fetch_failed", error=str(exc))
        raise RuntimeError(f"Failed to fetch plan data: {exc}")

    # 2. Build Exercise Composition
    used_exercise_ids = set()
    for w in workouts:
        for eid in w.get("exercise_ids", []):
            used_exercise_ids.add(eid)

    exercises_info = []
    for eid in used_exercise_ids:
        edef = exercise_defs.get(eid)
        if edef:
            name = edef.get("name", "Unknown")
            muscle = edef.get("target_muscle_group", "General")
            exercises_info.append(f"{name} ({muscle})")

    exercises_info.sort()
    exercise_composition = "\n".join([f"- {e}" for e in exercises_info])

    # 3. Call LLM
    if calendar_plan_id:
        prompt = TEMPLATE_ANALYSIS_PROMPT.format(
            plan_overview=context_str,
            exercise_composition=exercise_composition,
            user_focus=user_focus or "General structural analysis",
        )
    else:
        prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            plan_context=context_str,
            workout_history=history_context,
            exercise_composition=exercise_composition,
            analytics_metrics=analytics_context,
            user_focus=user_focus or "General structural analysis",
        )

    logger.info(
        "plan_analysis_llm_requested",
        user_id=user_id,
        plan_variant="template" if calendar_plan_id else "applied",
    )
    PLAN_ANALYSIS_REQUESTED_TOTAL.inc()

    result = await generate_structured_output(
        prompt=prompt,
        response_schema=ANALYSIS_RESPONSE_SCHEMA,
        temperature=0.4,
    )

    if not isinstance(result, dict):
        raise ValueError("Invalid LLM response format")

    return result


def create_plan_analysis_tool(user_id: str) -> ToolSpec:
    """ToolSpec for analyzing plan progress and getting recommendations."""

    parameters_schema = {
        "type": "object",
        "properties": {
            "applied_plan_id": {"type": "integer", "description": "ID of the applied plan to analyze (active plan)"},
            "calendar_plan_id": {"type": "integer", "description": "ID of the calendar plan to analyze (template)"},
            "focus": {
                "type": "string",
                "description": "Optional specific area to focus on (e.g., 'structure', 'volume', 'legs')",
            },
        },
    }

    async def handler(args: Dict[str, Any]) -> Dict[str, Any]:
        applied_plan_id = args.get("applied_plan_id")
        calendar_plan_id = args.get("calendar_plan_id")

        if not applied_plan_id and not calendar_plan_id:
            return {"error": "Please provide either applied_plan_id or calendar_plan_id"}

        focus = args.get("focus", "")

        try:
            analysis = await generate_plan_analysis(
                user_id=user_id,
                applied_plan_id=int(applied_plan_id) if applied_plan_id else None,
                calendar_plan_id=int(calendar_plan_id) if calendar_plan_id else None,
                user_focus=focus,
            )
            return analysis
        except Exception as e:
            return {"error": f"Analysis failed: {str(e)}"}

    return ToolSpec(
        name="analyze_plan_progress",
        description=(
            "Analyze the training plan structure, volume, and progress. Use this "
            "for 'analyze plan', 'describe plan', or 'how is my plan' requests."
        ),
        parameters_schema=parameters_schema,
        handler=handler,
    )
