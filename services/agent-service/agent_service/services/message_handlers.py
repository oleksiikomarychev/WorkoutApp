import asyncio
from collections.abc import Callable
from typing import Any

from celery.result import AsyncResult
from fastapi import WebSocket

from ..celery_app import celery_app
from ..prompts.simple_chat import PLAN_DETAILS_SYSTEM_PROMPT
from ..tasks.mass_edit_tasks import execute_applied_mass_edit_task, execute_mass_edit_agent_task
from .conversation_graph import fsm_plan_generator
from .message_command_parser import MessageCommand, MessageCommandKind
from .screen_tools_builder import ScreenToolsBuilder
from .simple_chat import simple_chat_generator
from .tool_agent import run_tools_agent
from .tool_result_dispatcher import ToolResultDispatcher


async def _stream_mass_edit_task(
    *,
    task,
    websocket: WebSocket,
    session_id: str,
    build_progress_payload: Callable[[str], dict[str, Any]],
    build_error_message: Callable[[Any], str],
    handle_success_result: Callable[[AsyncResult], "asyncio.Future[Any]"],
) -> None:
    previous_status = task.status
    while True:
        await asyncio.sleep(1.5)
        async_result = AsyncResult(task.id, app=celery_app)
        if async_result.status != previous_status:
            previous_status = async_result.status
            payload = {
                "type": "mass_edit_task",
                "event": "progress",
                "task_id": task.id,
                "status": async_result.status,
                "session_id": session_id,
            }
            extra = build_progress_payload(async_result.status) or {}
            payload.update(extra)
            await websocket.send_json(payload)

        if not async_result.ready():
            continue

        if async_result.failed():
            await websocket.send_json(
                {
                    "type": "message",
                    "role": "assistant",
                    "content": build_error_message(async_result.result),
                    "session_id": session_id,
                }
            )
            break

        await handle_success_result(async_result)
        break


class MassEditActiveHandler:
    def __init__(self, *, logger, get_active_applied_plan_id):
        self.logger = logger
        self.get_active_applied_plan_id = get_active_applied_plan_id

    async def handle(
        self,
        *,
        command: MessageCommand,
        websocket: WebSocket,
        session_id: str,
        user_id: str,
        chat_state: dict[str, Any] | None,
        fsm_state: dict[str, Any] | None,
        session_context: dict[str, Any],
        mode: str,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any], str, bool]:
        rest = command.rest
        if not rest:
            await websocket.send_json(
                {
                    "type": "message",
                    "role": "assistant",
                    "content": "Usage: /mass-edit <instructions>",
                    "session_id": session_id,
                }
            )
            return chat_state, fsm_state, session_context, mode, True

        instructions = rest
        applied_plan_id = await self.get_active_applied_plan_id(user_id)
        if not applied_plan_id:
            await websocket.send_json(
                {
                    "type": "message",
                    "role": "assistant",
                    "content": (
                        "No active applied plan found for this user. " "Please generate and apply a plan first."
                    ),
                    "session_id": session_id,
                }
            )
            return chat_state, fsm_state, session_context, mode, True

        task = execute_applied_mass_edit_task.delay(
            applied_plan_id=applied_plan_id,
            user_id=user_id,
            mode="apply",
            prompt=instructions,
        )

        await websocket.send_json(
            {
                "type": "mass_edit_task",
                "event": "submitted",
                "task_id": task.id,
                "status": task.status,
                "session_id": session_id,
                "variant": "applied_plan",
                "applied_plan_id": applied_plan_id,
            }
        )

        async def _handle_success(async_result: AsyncResult) -> None:
            payload = async_result.result or {}
            summary = payload.get("summary") or {}
            reply_text = "AI mass edit for your active plan has been processed."
            await websocket.send_json(
                {
                    "type": "message",
                    "role": "assistant",
                    "content": reply_text,
                    "session_id": session_id,
                }
            )
            await websocket.send_json(
                {
                    "type": "mass_edit_result",
                    "session_id": session_id,
                    "task_id": task.id,
                    "variant": payload.get("variant"),
                    "mode": payload.get("mode"),
                    "applied_plan_id": payload.get("applied_plan_id"),
                    "summary": summary,
                    "mass_edit_command": payload.get("mass_edit_command"),
                }
            )

        await _stream_mass_edit_task(
            task=task,
            websocket=websocket,
            session_id=session_id,
            build_progress_payload=lambda status: {"variant": "applied_plan"},
            build_error_message=lambda err: f"Applied-plan mass edit failed: {err}",
            handle_success_result=_handle_success,
        )

        return chat_state, fsm_state, session_context, mode, True


class MassEditFlexHandler:
    def __init__(self, *, logger):
        self.logger = logger

    async def handle(
        self,
        *,
        command: MessageCommand,
        websocket: WebSocket,
        session_id: str,
        user_id: str,
        chat_state: dict[str, Any] | None,
        fsm_state: dict[str, Any] | None,
        session_context: dict[str, Any],
        mode: str,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any], str, bool]:
        rest = command.rest
        if not rest:
            await websocket.send_json(
                {
                    "type": "message",
                    "role": "assistant",
                    "content": "Usage: /mass_edit <plan_id> [mode]: <instructions>",
                    "session_id": session_id,
                }
            )
            return chat_state, fsm_state, session_context, mode, True

        ctx_target = session_context.get("default_mass_edit_target")
        ctx_entities = session_context.get("entities") or {}
        ctx_applied_plan = ctx_entities.get("active_applied_plan") or {}
        ctx_applied_plan_id = ctx_applied_plan.get("id") if isinstance(ctx_applied_plan, dict) else None

        header = rest
        instructions = ""
        if ":" in rest:
            header, instructions = rest.split(":", 1)
            header = header.strip()
            instructions = instructions.strip()
        else:
            header = header.strip()

        tokens = [p for p in header.split(" ") if p]
        mass_edit_mode = "apply"
        plan_id: int | None = None
        use_applied_plan = False

        if tokens:
            first_token = tokens[0]
            lower_first = first_token.lower()

            plan_id_candidate: int | None = None
            try:
                plan_id_candidate = int(first_token)
            except ValueError:
                plan_id_candidate = None

            if plan_id_candidate is not None:
                plan_id = plan_id_candidate
                if len(tokens) >= 2 and tokens[1].lower() in {"apply", "preview"}:
                    mass_edit_mode = tokens[1].lower()
                if not instructions:
                    start_idx = 2 if len(tokens) >= 2 and tokens[1].lower() in {"apply", "preview"} else 1
                    instructions = " ".join(tokens[start_idx:]).strip()
            else:
                if lower_first in {"apply", "preview"}:
                    mass_edit_mode = lower_first
                    if not instructions:
                        instructions = " ".join(tokens[1:]).strip()
                else:
                    if not instructions:
                        instructions = " ".join(tokens).strip()

        if plan_id is None and ctx_target == "applied" and ctx_applied_plan_id:
            use_applied_plan = True
            self.logger.info(
                "mass_edit_auto_substitution",
                session_id=session_id,
                applied_plan_id=ctx_applied_plan_id,
                screen=session_context.get("screen"),
            )
        elif plan_id is None:
            await websocket.send_json(
                {
                    "type": "message",
                    "role": "assistant",
                    "content": (
                        "Could not determine plan. Either provide plan_id explicitly "
                        "(/mass_edit <plan_id> [mode]: instructions) or open chat from "
                        "the Active Plan screen for auto-detection."
                    ),
                    "session_id": session_id,
                }
            )
            return chat_state, fsm_state, session_context, mode, True

        if not instructions:
            await websocket.send_json(
                {
                    "type": "message",
                    "role": "assistant",
                    "content": "Please provide instructions in /mass_edit.",
                    "session_id": session_id,
                }
            )
            return chat_state, fsm_state, session_context, mode, True

        if use_applied_plan:
            task = execute_applied_mass_edit_task.delay(
                applied_plan_id=ctx_applied_plan_id,
                user_id=user_id,
                mode=mass_edit_mode,
                prompt=instructions,
            )
            await websocket.send_json(
                {
                    "type": "mass_edit_task",
                    "event": "submitted",
                    "task_id": task.id,
                    "status": task.status,
                    "session_id": session_id,
                    "variant": "applied_plan",
                    "applied_plan_id": ctx_applied_plan_id,
                }
            )
        else:
            task = execute_mass_edit_agent_task.delay(
                plan_id=plan_id,
                user_id=user_id,
                mode=mass_edit_mode,
                prompt=instructions,
            )
            await websocket.send_json(
                {
                    "type": "mass_edit_task",
                    "event": "submitted",
                    "task_id": task.id,
                    "status": task.status,
                    "session_id": session_id,
                    "variant": "calendar_plan",
                    "plan_id": plan_id,
                }
            )

        task_variant = "applied_plan" if use_applied_plan else "calendar_plan"

        async def _handle_success(async_result: AsyncResult) -> None:
            payload = async_result.result or {}

            if task_variant == "applied_plan":
                summary = payload.get("summary") or {}
                reply_text = "AI mass edit for your active plan has been processed."
                await websocket.send_json(
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": reply_text,
                        "session_id": session_id,
                    }
                )
                await websocket.send_json(
                    {
                        "type": "mass_edit_result",
                        "session_id": session_id,
                        "task_id": task.id,
                        "variant": "applied_plan",
                        "mode": payload.get("mode"),
                        "applied_plan_id": payload.get("applied_plan_id"),
                        "summary": summary,
                        "mass_edit_command": payload.get("mass_edit_command"),
                    }
                )
            else:
                reply_text = payload.get("assistant_message") or "AI mass edit has been processed."
                await websocket.send_json(
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": reply_text,
                        "session_id": session_id,
                    }
                )
                await websocket.send_json(
                    {
                        "type": "mass_edit_result",
                        "session_id": session_id,
                        "task_id": task.id,
                        "variant": "calendar_plan",
                        "decision_type": payload.get("decision_type"),
                        "tool_name": payload.get("tool_name"),
                        "mode": payload.get("mode"),
                        "plan_id": payload.get("plan_id"),
                        "plan": payload.get("plan"),
                        "mass_edit_command": payload.get("mass_edit_command"),
                        "raw_decision": payload.get("raw_decision"),
                        "assistant_message": payload.get("assistant_message"),
                    }
                )

        await _stream_mass_edit_task(
            task=task,
            websocket=websocket,
            session_id=session_id,
            build_progress_payload=lambda status: {},
            build_error_message=lambda err: f"Mass edit failed: {err}",
            handle_success_result=_handle_success,
        )

        return chat_state, fsm_state, session_context, mode, True


class FsmHandler:
    async def handle(
        self,
        *,
        command: MessageCommand,
        content: str,
        websocket: WebSocket,
        session_id: str,
        user_id: str,
        chat_state: dict[str, Any] | None,
        fsm_state: dict[str, Any] | None,
        session_context: dict[str, Any],
        mode: str,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any], str, bool]:
        if command.kind == MessageCommandKind.FSM_ACTIVATE:
            mode = "fsm"
            fsm_state = None
            await websocket.send_json(
                {
                    "type": "message",
                    "role": "assistant",
                    "content": "Switched to training plan generation mode. Please describe your workout goal.",
                    "session_id": session_id,
                }
            )
            return chat_state, fsm_state, session_context, mode, True

        if mode == "fsm":
            reply, done, fsm_state = await fsm_plan_generator(
                content,
                state=fsm_state,
                user_id=user_id,
            )
            if reply:
                await websocket.send_json(
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": reply,
                        "session_id": session_id,
                    }
                )
            if done:
                await websocket.send_json({"type": "done", "session_id": session_id})
                mode = "chat"
                fsm_state = None
            return chat_state, fsm_state, session_context, mode, True

        return chat_state, fsm_state, session_context, mode, False


class PlainChatHandler:
    def __init__(self, *, logger):
        self.logger = logger
        self.screen_tools_builder = ScreenToolsBuilder()
        self.tool_result_dispatcher = ToolResultDispatcher()

    async def handle(
        self,
        *,
        content: str,
        websocket: WebSocket,
        session_id: str,
        user_id: str,
        chat_state: dict[str, Any] | None,
        fsm_state: dict[str, Any] | None,
        session_context: dict[str, Any],
        mode: str,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any], str, bool]:
        screen = session_context.get("screen")

        tools: Any = []
        arguments_prompt: str | None = None
        active_applied_plan_id: int | None = None

        if screen is not None:
            screen_config = await self.screen_tools_builder.build(
                screen=screen,
                session_context=session_context,
                user_id=user_id,
                content=content,
            )
            tools = screen_config.tools
            arguments_prompt = screen_config.arguments_prompt
            active_applied_plan_id = screen_config.active_applied_plan_id

        if tools and arguments_prompt:
            try:
                result = await run_tools_agent(
                    user_prompt=arguments_prompt,
                    tools=tools,
                    temperature=0.2,
                )
            except Exception as exc:
                self.logger.exception("tools_agent_failed", exc_info=exc)
                result = None

            handled = False
            if result and result.decision_type == "tool_call" and isinstance(result.tool_result, dict):
                chat_state, handled = await self.tool_result_dispatcher.dispatch(
                    result=result,
                    websocket=websocket,
                    session_id=session_id,
                    user_id=user_id,
                    chat_state=chat_state,
                    content=content,
                    active_applied_plan_id=active_applied_plan_id,
                )
            if handled:
                return chat_state, fsm_state, session_context, mode, True

        system_prompt_for_screen = None
        if screen == "plan_details":
            system_prompt_for_screen = PLAN_DETAILS_SYSTEM_PROMPT
        result = await simple_chat_generator(
            content,
            state=chat_state,
            user_id=user_id,
            system_prompt=system_prompt_for_screen,
        )
        chat_state = result.get("state") if isinstance(result.get("state"), dict) else chat_state
        reply = result.get("reply")
        if reply:
            await websocket.send_json(
                {
                    "type": "message",
                    "role": "assistant",
                    "content": reply,
                    "session_id": session_id,
                }
            )

        return chat_state, fsm_state, session_context, mode, True
