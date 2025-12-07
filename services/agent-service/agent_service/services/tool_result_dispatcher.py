from typing import Any

from fastapi import WebSocket

from ..prompts.analytics_summary import (
    build_analyze_coach_athletes_portfolio_prompt,
    build_analyze_completed_workouts_prompt,
    build_analyze_plan_macros_prompt,
    build_analyze_user_max_prompt,
)
from .simple_chat import simple_chat_generator


class ToolResultDispatcher:
    async def dispatch(
        self,
        result: Any,
        websocket: WebSocket,
        session_id: str,
        user_id: str,
        chat_state: dict[str, Any] | None,
        content: str,
        active_applied_plan_id: int | None,
    ) -> tuple[dict[str, Any] | None, bool]:
        tool_res = result.tool_result
        tool_name = result.tool_name

        if tool_name == "applied_plan_schedule_shift":
            summary = tool_res.get("summary") or {}
            command = tool_res.get("schedule_shift_command") or {}
            mode = tool_res.get("mode") or "apply"

            workouts_shifted = summary.get("workouts_shifted")
            days = summary.get("days")
            msg = "Schedule shift applied."
            if workouts_shifted is not None and days is not None:
                msg = f"Shifted {workouts_shifted} workouts by {days} day(s)."

            await websocket.send_json(
                {
                    "type": "message",
                    "role": "assistant",
                    "content": msg,
                    "session_id": session_id,
                }
            )

            await websocket.send_json(
                {
                    "type": "mass_edit_result",
                    "session_id": session_id,
                    "variant": "applied_schedule_shift",
                    "mode": mode,
                    "applied_plan_id": active_applied_plan_id,
                    "summary": summary,
                    "schedule_shift_command": command,
                }
            )

            return chat_state, True

        if tool_name == "applied_plan_mass_edit":
            summary = tool_res.get("summary") or {}
            command = tool_res.get("mass_edit_command")
            cmd_mode = None
            if isinstance(command, dict):
                cmd_mode = command.get("mode")

            mode = summary.get("mode") or cmd_mode or "preview"

            w_matched = summary.get("workouts_matched", 0)
            sets_matched = summary.get("sets_matched", 0)
            sets_modified = summary.get("sets_modified", 0)

            if mode == "apply":
                msg = f"Plan updated: {w_matched} workouts matched, {sets_modified} sets modified."
            else:
                msg = (
                    "Preview of changes: "
                    f"{w_matched} workouts would be affected, "
                    f"{sets_matched} sets would be updated if you apply these changes."
                )

            await websocket.send_json(
                {
                    "type": "message",
                    "role": "assistant",
                    "content": msg,
                    "session_id": session_id,
                }
            )

            await websocket.send_json(
                {
                    "type": "mass_edit_result",
                    "session_id": session_id,
                    "variant": "applied_plan",
                    "mode": mode,
                    "applied_plan_id": active_applied_plan_id,
                    "summary": summary,
                    "mass_edit_command": command,
                    "instructions": tool_res.get("instructions"),
                }
            )

            return chat_state, True

        if tool_name == "analyze_plan_progress":
            error_msg = tool_res.get("error")
            if error_msg:
                msg = f"Не удалось проанализировать план: {error_msg}"
                await websocket.send_json(
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": msg,
                        "session_id": session_id,
                    }
                )
            else:
                summary_text = tool_res.get("summary", "")
                recs = tool_res.get("recommendations", [])

                msg_parts = []
                if summary_text:
                    msg_parts.append(summary_text)
                if recs:
                    msg_parts.append("\n**Recommendations:**")
                    for r in recs:
                        msg_parts.append(f"- {r}")
                if not msg_parts:
                    msg_parts.append(
                        "План проанализирован, но нет данных для подробного текста. "
                        "Попробуй переформулировать запрос или уточнить, что именно нужно."
                    )

                await websocket.send_json(
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": "\n".join(msg_parts),
                        "session_id": session_id,
                    }
                )

            return chat_state, True

        if tool_name == "analyze_plan_macros":
            prompt_context = build_analyze_plan_macros_prompt(tool_res, content)

            chat_res = await simple_chat_generator(
                prompt_context,
                state=chat_state,
                user_id=user_id,
            )
            chat_state = chat_res.get("state")
            reply = chat_res.get("reply")

            await websocket.send_json(
                {
                    "type": "message",
                    "role": "assistant",
                    "content": reply,
                    "session_id": session_id,
                }
            )

            return chat_state, True

        if tool_name == "create_manage_macros":
            if tool_res.get("error"):
                msg = f"Failed to create macro: {tool_res['error']}"
            else:
                m_name = tool_res.get("details", {}).get("name", "Macro")
                msg = f"✅ Successfully created macro: **{m_name}**. It is now active for your plan."

            await websocket.send_json(
                {
                    "type": "message",
                    "role": "assistant",
                    "content": msg,
                    "session_id": session_id,
                }
            )

            return chat_state, True

        if tool_name == "analyze_user_max_data":
            prompt_context = build_analyze_user_max_prompt(tool_res, content)

            chat_res = await simple_chat_generator(
                prompt_context,
                state=chat_state,
                user_id=user_id,
            )
            chat_state = chat_res.get("state")
            reply = chat_res.get("reply")

            await websocket.send_json(
                {
                    "type": "message",
                    "role": "assistant",
                    "content": reply,
                    "session_id": session_id,
                }
            )

            return chat_state, True

        if tool_name == "analyze_completed_workouts":
            prompt_context = build_analyze_completed_workouts_prompt(tool_res, content)

            chat_res = await simple_chat_generator(
                prompt_context,
                state=chat_state,
                user_id=user_id,
            )
            chat_state = chat_res.get("state")
            reply = chat_res.get("reply")

            await websocket.send_json(
                {
                    "type": "message",
                    "role": "assistant",
                    "content": reply,
                    "session_id": session_id,
                }
            )

            return chat_state, True

        if tool_name == "analyze_coach_athletes_portfolio":
            prompt_context = build_analyze_coach_athletes_portfolio_prompt(tool_res, content)

            chat_res = await simple_chat_generator(
                prompt_context,
                state=chat_state,
                user_id=user_id,
            )
            chat_state = chat_res.get("state")
            reply = chat_res.get("reply")

            await websocket.send_json(
                {
                    "type": "message",
                    "role": "assistant",
                    "content": reply,
                    "session_id": session_id,
                }
            )

            return chat_state, True

        await websocket.send_json(
            {
                "type": "message",
                "role": "assistant",
                "content": "Action completed.",
                "session_id": session_id,
            }
        )

        return chat_state, True
