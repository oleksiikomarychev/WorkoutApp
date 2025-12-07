from dataclasses import dataclass
from typing import Any

from ..prompts.tool_agent import (
    build_active_plan_tools_arguments_prompt,
    build_coach_athlete_plan_tools_arguments_prompt,
    build_coach_athletes_tools_arguments_prompt,
)
from .coach_athlete_analysis import analyze_athlete_history_tool
from .coach_portfolio_analysis import analyze_coach_athletes_portfolio_tool
from .entity_resolver import (
    build_resolved_inline_entities_snippet,
    parse_inline_references,
)
from .history_analysis import analyze_completed_workouts_tool
from .macros_analysis import create_macros_analysis_tool
from .macros_manager import create_manage_macros_tool
from .mass_edit import (
    create_applied_plan_mass_edit_tool,
    create_applied_plan_schedule_shift_tool,
)
from .plan_analysis import create_plan_analysis_tool
from .user_max_analysis import analyze_user_max_tool


@dataclass
class ScreenToolsConfig:
    tools: list[Any]
    arguments_prompt: str | None
    active_applied_plan_id: int | None


class ScreenToolsBuilder:
    async def build(
        self,
        *,
        screen: str | None,
        session_context: dict[str, Any],
        user_id: str,
        content: str,
    ) -> ScreenToolsConfig:
        tools: list[Any] = []
        arguments_prompt: str | None = None
        active_applied_plan_id: int | None = None

        if screen == "active_plan":
            tools = [
                create_applied_plan_schedule_shift_tool(user_id),
                create_applied_plan_mass_edit_tool(user_id),
                create_plan_analysis_tool(user_id),
            ]

            selection = session_context.get("selection") or {}
            selection_date = selection.get("date")
            entities = session_context.get("entities") or {}
            active_applied_plan = entities.get("active_applied_plan") or {}
            active_applied_plan_id = active_applied_plan.get("id") if isinstance(active_applied_plan, dict) else None

            inline_refs = parse_inline_references(content)
            inline_snippet = await build_resolved_inline_entities_snippet(
                inline_refs,
                selection_date=selection_date,
                active_applied_plan_id=active_applied_plan_id,
            )
            user_instructions = content
            if inline_snippet:
                user_instructions = f"{content}\n\n{inline_snippet}"

            arguments_prompt = build_active_plan_tools_arguments_prompt(
                selection_date=selection_date,
                active_applied_plan_id=active_applied_plan_id,
                user_instructions=user_instructions,
            )
        elif screen == "coach_athlete_plan":
            tools = [
                create_applied_plan_mass_edit_tool(user_id),
                create_plan_analysis_tool(user_id),
                analyze_athlete_history_tool(user_id),
            ]

            selection = session_context.get("selection") or {}
            selection_date = selection.get("date")
            athlete_id = selection.get("athlete_id")
            athlete_name = selection.get("athlete_name")
            entities = session_context.get("entities") or {}
            active_applied_plan = entities.get("active_applied_plan") or {}
            active_applied_plan_id = active_applied_plan.get("id") if isinstance(active_applied_plan, dict) else None

            inline_refs = parse_inline_references(content)
            inline_snippet = await build_resolved_inline_entities_snippet(
                inline_refs,
                selection_date=selection_date,
                active_applied_plan_id=active_applied_plan_id,
            )
            user_instructions = content
            if inline_snippet:
                user_instructions = f"{content}\n\n{inline_snippet}"

            arguments_prompt = build_coach_athlete_plan_tools_arguments_prompt(
                selection_date=selection_date,
                athlete_id=athlete_id,
                athlete_name=athlete_name,
                active_applied_plan_id=active_applied_plan_id,
                user_instructions=user_instructions,
            )
        elif screen == "user_profile":
            tools = [
                analyze_completed_workouts_tool(user_id),
            ]
            arguments_prompt = (
                "Screen: user_profile. The user is viewing their global training stats and profile. "
                f"User message: {content}"
            )
        elif screen in ("user_max", "analytics"):
            tools = [
                analyze_user_max_tool(user_id),
            ]
            arguments_prompt = (
                f"Screen: {screen}. The user is viewing strength/analytics data. " f"User message: {content}"
            )
        elif screen == "plan_details":
            c_plan_id = session_context.get("calendar_plan_id")
            a_plan_id = session_context.get("applied_plan_id")

            tools = [
                create_macros_analysis_tool(user_id),
                create_manage_macros_tool(user_id),
                create_plan_analysis_tool(user_id),
            ]

            context_info = []
            if c_plan_id:
                context_info.append(f"CalendarPlanID={c_plan_id}")
            if a_plan_id:
                context_info.append(f"AppliedPlanID={a_plan_id}")

            ctx_str = ", ".join(context_info)

            arguments_prompt = (
                "Screen: plan_details inside WorkoutApp. In this screen the word 'macros' "
                "ALWAYS refers to training plan macros (automation rules attached to the "
                "training plan), NOT nutrition macros like protein, fats, or carbs, "
                "unless the user is clearly asking about food or diet. "
                f"Context: {ctx_str}. "
                "If the user asks about creating, editing, enabling, disabling, or "
                "understanding macros, you MUST call one of the macros tools: "
                "'create_manage_macros' to create/update rules, or 'analyze_plan_macros' "
                "to list and explain the existing automation rules for this plan. "
                "Only answer directly if the question is clearly not about training "
                "plan macros. "
                f"User message: {content}"
            )

        elif screen == "coach_athletes":
            tools = [
                analyze_coach_athletes_portfolio_tool(user_id),
            ]

            selection = session_context.get("selection") or {}
            segment_filter = selection.get("segment_filter")
            min_sessions = selection.get("min_sessions_per_week")
            min_adherence = selection.get("min_plan_adherence")
            sort = selection.get("sort")

            arguments_prompt = build_coach_athletes_tools_arguments_prompt(
                segment_filter=segment_filter,
                min_sessions_per_week=min_sessions,
                min_plan_adherence=min_adherence,
                sort=sort,
                user_instructions=content,
            )

        return ScreenToolsConfig(
            tools=tools,
            arguments_prompt=arguments_prompt,
            active_applied_plan_id=active_applied_plan_id,
        )
