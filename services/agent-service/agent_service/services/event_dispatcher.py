from typing import Any

from fastapi import WebSocket

from .mass_edit import (
    apply_applied_mass_edit_to_plan,
    shift_applied_plan_schedule,
)
from .message_command_parser import MessageCommandKind, MessageCommandParser
from .message_handlers import (
    FsmHandler,
    MassEditActiveHandler,
    MassEditFlexHandler,
    PlainChatHandler,
)


class EventDispatcher:
    def __init__(self, *, logger, get_active_applied_plan_id):
        self.logger = logger
        self.get_active_applied_plan_id = get_active_applied_plan_id
        self.message_command_parser = MessageCommandParser()
        self.mass_edit_active_handler = MassEditActiveHandler(
            logger=logger,
            get_active_applied_plan_id=get_active_applied_plan_id,
        )
        self.mass_edit_flex_handler = MassEditFlexHandler(logger=logger)
        self.fsm_handler = FsmHandler()
        self.plain_chat_handler = PlainChatHandler(logger=logger)

    async def dispatch(
        self,
        *,
        data: dict[str, Any],
        websocket: WebSocket,
        session_id: str,
        user_id: str,
        chat_state: dict[str, Any] | None,
        fsm_state: dict[str, Any] | None,
        session_context: dict[str, Any],
        mode: str,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any], str, bool]:
        event_type = data.get("type")

        if event_type == "context":
            session_context = data.get("payload") or {}
            self.logger.info(
                "session_context_received",
                session_id=session_id,
                screen=session_context.get("screen"),
                default_mass_edit_target=session_context.get("default_mass_edit_target"),
            )
            return chat_state, fsm_state, session_context, mode, True

        if event_type == "mass_edit_apply":
            await self._handle_mass_edit_apply(
                data=data,
                websocket=websocket,
                session_id=session_id,
                user_id=user_id,
            )
            return chat_state, fsm_state, session_context, mode, True

        if event_type == "schedule_shift_apply":
            await self._handle_schedule_shift_apply(
                data=data,
                websocket=websocket,
                session_id=session_id,
                user_id=user_id,
            )
            return chat_state, fsm_state, session_context, mode, True

        if event_type == "message":
            return await self._handle_message(
                data=data,
                websocket=websocket,
                session_id=session_id,
                user_id=user_id,
                chat_state=chat_state,
                fsm_state=fsm_state,
                session_context=session_context,
                mode=mode,
            )

        if event_type == "ping":
            await websocket.send_json({"type": "pong", "session_id": session_id})
            return chat_state, fsm_state, session_context, mode, True

        return chat_state, fsm_state, session_context, mode, False

    async def _handle_mass_edit_apply(
        self,
        *,
        data: dict[str, Any],
        websocket: WebSocket,
        session_id: str,
        user_id: str,
    ) -> None:
        variant = data.get("variant") or "applied_plan"
        if variant != "applied_plan":
            await websocket.send_json(
                {
                    "type": "message",
                    "role": "assistant",
                    "content": "Unsupported mass_edit_apply variant.",
                    "session_id": session_id,
                }
            )
            return

        raw_applied_plan_id = data.get("applied_plan_id")
        command = data.get("mass_edit_command") or data.get("command")

        try:
            applied_plan_id = int(raw_applied_plan_id)
        except (TypeError, ValueError):
            await websocket.send_json(
                {
                    "type": "message",
                    "role": "assistant",
                    "content": "Failed to apply changes: invalid applied_plan_id.",
                    "session_id": session_id,
                }
            )
            return

        if not isinstance(command, dict):
            await websocket.send_json(
                {
                    "type": "message",
                    "role": "assistant",
                    "content": "Failed to apply changes: invalid mass edit command payload.",
                    "session_id": session_id,
                }
            )
            return

        command["mode"] = "apply"

        try:
            summary = await apply_applied_mass_edit_to_plan(
                applied_plan_id=applied_plan_id,
                user_id=user_id,
                command=command,
            )
        except Exception as exc:  # pragma: no cover - best-effort logging
            self.logger.exception("applied_mass_edit_apply_from_preview_failed", exc_info=exc)
            await websocket.send_json(
                {
                    "type": "message",
                    "role": "assistant",
                    "content": "Не удалось применить изменения к активному плану.",
                    "session_id": session_id,
                }
            )
            return

        w_matched = summary.get("workouts_matched", 0)
        s_modified = summary.get("sets_modified", 0)
        msg = f"Plan updated: {w_matched} workouts matched, {s_modified} sets modified."

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
                "mode": "apply",
                "applied_plan_id": applied_plan_id,
                "summary": summary,
                "mass_edit_command": command,
            }
        )

    async def _handle_schedule_shift_apply(
        self,
        *,
        data: dict[str, Any],
        websocket: WebSocket,
        session_id: str,
        user_id: str,
    ) -> None:
        variant = data.get("variant") or "applied_schedule_shift"
        if variant != "applied_schedule_shift":
            await websocket.send_json(
                {
                    "type": "message",
                    "role": "assistant",
                    "content": "Unsupported schedule_shift_apply variant.",
                    "session_id": session_id,
                }
            )
            return

        raw_applied_plan_id = data.get("applied_plan_id")
        command = data.get("schedule_shift_command") or data.get("command")

        try:
            applied_plan_id = int(raw_applied_plan_id)
        except Exception:
            await websocket.send_json(
                {
                    "type": "message",
                    "role": "assistant",
                    "content": "Failed to apply schedule shift: invalid applied_plan_id.",
                    "session_id": session_id,
                }
            )
            return

        if not isinstance(command, dict):
            await websocket.send_json(
                {
                    "type": "message",
                    "role": "assistant",
                    "content": "Failed to apply schedule shift: invalid command payload.",
                    "session_id": session_id,
                }
            )
            return

        from_date_val = str(command.get("from_date") or "").strip()
        if not from_date_val:
            await websocket.send_json(
                {
                    "type": "message",
                    "role": "assistant",
                    "content": "Failed to apply schedule shift: invalid from_date.",
                    "session_id": session_id,
                }
            )
            return

        to_date_val = command.get("to_date")
        if to_date_val is not None:
            to_date_val = str(to_date_val).strip() or None

        days_val = command.get("days", 0)
        try:
            days = int(days_val)
        except (TypeError, ValueError):
            days = 0

        new_rest_days = command.get("new_rest_days")
        if new_rest_days is not None:
            try:
                new_rest_days = int(new_rest_days)
            except (TypeError, ValueError):
                new_rest_days = None

        action_type = command.get("action_type") or "shift"
        if action_type not in ("shift", "set_rest"):
            action_type = "shift"

        only_future = bool(command.get("only_future", False))
        status_in = command.get("status_in")
        if status_in is not None and not isinstance(status_in, list):
            status_in = None

        try:
            summary = await shift_applied_plan_schedule(
                applied_plan_id=applied_plan_id,
                user_id=user_id,
                from_date=from_date_val,
                to_date=to_date_val,
                days=days,
                new_rest_days=new_rest_days,
                action_type=action_type,
                only_future=only_future,
                status_in=status_in,
                mode="apply",
            )
        except Exception as exc:  # pragma: no cover - best-effort logging
            self.logger.exception("applied_schedule_shift_apply_from_preview_failed", exc_info=exc)
            await websocket.send_json(
                {
                    "type": "message",
                    "role": "assistant",
                    "content": "Не удалось применить сдвиг расписания активного плана.",
                    "session_id": session_id,
                }
            )
            return

        w_shifted = summary.get("workouts_shifted", 0)
        d_applied = summary.get("days", days)
        msg = f"Shifted {w_shifted} workouts by {d_applied} day(s)."

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
                "mode": "apply",
                "applied_plan_id": applied_plan_id,
                "summary": summary,
                "schedule_shift_command": command,
            }
        )

    async def _handle_message(
        self,
        *,
        data: dict[str, Any],
        websocket: WebSocket,
        session_id: str,
        user_id: str,
        chat_state: dict[str, Any] | None,
        fsm_state: dict[str, Any] | None,
        session_context: dict[str, Any],
        mode: str,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any], str, bool]:
        content = str(data.get("content", ""))
        command = self.message_command_parser.parse(content)

        if command.kind == MessageCommandKind.MASS_EDIT_ACTIVE:
            return await self.mass_edit_active_handler.handle(
                command=command,
                websocket=websocket,
                session_id=session_id,
                user_id=user_id,
                chat_state=chat_state,
                fsm_state=fsm_state,
                session_context=session_context,
                mode=mode,
            )

        if command.kind == MessageCommandKind.MASS_EDIT_FLEX:
            return await self.mass_edit_flex_handler.handle(
                command=command,
                websocket=websocket,
                session_id=session_id,
                user_id=user_id,
                chat_state=chat_state,
                fsm_state=fsm_state,
                session_context=session_context,
                mode=mode,
            )

        chat_state, fsm_state, session_context, mode, handled = await self.fsm_handler.handle(
            command=command,
            content=content,
            websocket=websocket,
            session_id=session_id,
            user_id=user_id,
            chat_state=chat_state,
            fsm_state=fsm_state,
            session_context=session_context,
            mode=mode,
        )
        if handled:
            return chat_state, fsm_state, session_context, mode, True

        return await self.plain_chat_handler.handle(
            content=content,
            websocket=websocket,
            session_id=session_id,
            user_id=user_id,
            chat_state=chat_state,
            fsm_state=fsm_state,
            session_context=session_context,
            mode=mode,
        )
