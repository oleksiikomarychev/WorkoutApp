from typing import Any


def build_tools_decision_system_prompt(tools_block: str) -> str:
    return (
        "You are an AI assistant with access to tools.\n\n"
        "You MUST respond strictly as JSON matching the given schema.\n\n"
        "Available tools (each with a JSON parameters schema describing its input):\n"
        f"{tools_block}\n\n"
        "If you decide to call a tool, respond as:\n"
        "{\n"
        '  "type": "tool_call",\n'
        '  "tool": "<tool_name>",\n'
        '  "arguments": { ... }\n'
        "}\n\n"
        "If you decide to answer directly, respond as:\n"
        "{\n"
        '  "type": "answer",\n'
        '  "answer": "<final natural language answer>"\n'
        "}\n"
    )


def build_active_plan_context_snippet(selection_date: Any, active_applied_plan_id: Any) -> str:
    return (
        f"Screen: active_plan. Selection date: {selection_date}. "
        f"Active applied_plan_id: {active_applied_plan_id}. "
        "If the user asks to shift workouts schedule, use `applied_plan_schedule_shift`. "
        "If the user asks to modify exercises, sets, or volume (mass edit), use `applied_plan_mass_edit`. "
        "If the user asks ANY questions about the plan content, exercise selection, "
        "balance, progress, or asks for critique/advice, YOU MUST use `analyze_plan_progress`. "
        "Always use applied_plan_id from context."
    )


def build_active_plan_tools_arguments_prompt(
    selection_date: Any,
    active_applied_plan_id: Any,
    user_instructions: str,
) -> str:
    context_snippet = build_active_plan_context_snippet(selection_date, active_applied_plan_id)
    return f"Context: {context_snippet}\nUser instructions: {user_instructions}"


def build_coach_athlete_plan_context_snippet(
    selection_date: Any,
    athlete_id: Any,
    athlete_name: Any,
    active_applied_plan_id: Any,
) -> str:
    return (
        "Screen: coach_athlete_plan. The coach is viewing an athlete's active training plan. "
        f"Selection date: {selection_date}. "
        f"Athlete_id: {athlete_id}, athlete_name: {athlete_name}. "
        f"Active applied_plan_id: {active_applied_plan_id}. "
        "If the user asks to modify exercises, sets, or volume in this athlete's active plan, "
        "use `applied_plan_mass_edit` and always pass applied_plan_id from context. "
        "If the user asks about the plan content, structure, balance, or progress for this athlete, "
        "YOU MUST use `analyze_plan_progress` with applied_plan_id from context, and on this "
        "screen you MUST also pass athlete_id from context in the `athlete_id` argument so that "
        "backend requests are executed as this athlete (not as the coach). "
        "If the user asks about this athlete's broader training history, consistency, or long-term "
        "trends beyond the current plan, use `analyze_athlete_history` and pass athlete_id (and days "
        "if needed). The `analyze_athlete_history` tool returns both the requested `days` interval, "
        "an internal `weeks` window used by the CRM analytics endpoint, and a rich `raw` object "
        "with detailed athlete analytics (sessions, plan metrics, segments, muscle groups, trends). "
        "Always inspect the `raw` structure returned by the tool instead of guessing field names. "
    )


def build_coach_athlete_plan_tools_arguments_prompt(
    selection_date: Any,
    athlete_id: Any,
    athlete_name: Any,
    active_applied_plan_id: Any,
    user_instructions: str,
) -> str:
    context_snippet = build_coach_athlete_plan_context_snippet(
        selection_date=selection_date,
        athlete_id=athlete_id,
        athlete_name=athlete_name,
        active_applied_plan_id=active_applied_plan_id,
    )
    return f"Context: {context_snippet}\nUser instructions: {user_instructions}"


def build_coach_athletes_context_snippet(
    segment_filter: Any,
    min_sessions_per_week: Any,
    min_plan_adherence: Any,
    sort: Any,
) -> str:
    return (
        "Screen: coach_athletes. The coach is viewing a portfolio of athletes with filters applied. "
        f"Segment_filter: {segment_filter}. "
        f"Min_sessions_per_week: {min_sessions_per_week}. "
        f"Min_plan_adherence (0-1): {min_plan_adherence}. "
        f"Sort: {sort}. "
        "If the user asks which athletes or segments to prioritize, who is at risk, or how different "
        "groups of athletes compare, YOU MUST use `analyze_coach_athletes_portfolio`. "
        "Always rely on the current filters and sorting from context when deciding what to analyze. "
        "The `analyze_coach_athletes_portfolio` tool returns a `filters` object (including the "
        "current segment_filter, min_sessions_per_week, min_plan_adherence, sort, days and weeks) "
        "and a rich `raw` object with CRM-based analytics for each athlete (sessions per week, "
        "adherence, recency, segments, and other aggregates). Always inspect these returned "
        "structures when reasoning about the portfolio. "
    )


def build_coach_athletes_tools_arguments_prompt(
    segment_filter: Any,
    min_sessions_per_week: Any,
    min_plan_adherence: Any,
    sort: Any,
    user_instructions: str,
) -> str:
    context_snippet = build_coach_athletes_context_snippet(
        segment_filter=segment_filter,
        min_sessions_per_week=min_sessions_per_week,
        min_plan_adherence=min_plan_adherence,
        sort=sort,
    )
    return f"Context: {context_snippet}\nUser instructions: {user_instructions}"
