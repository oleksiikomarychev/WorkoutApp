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
