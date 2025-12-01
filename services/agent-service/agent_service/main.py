import asyncio
import json
import os
from typing import Any, Dict, Optional
from uuid import uuid4

import httpx
import structlog
from celery.result import AsyncResult
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from google.auth.transport import requests
from google.oauth2 import id_token
from prometheus_fastapi_instrumentator import Instrumentator

from .celery_app import celery_app
from .config import settings
from .logging_config import configure_logging
from .prompts.tool_agent import build_active_plan_tools_arguments_prompt
from .routers import avatars, plan_mass_edit, training_plans
from .services.conversation_graph import fsm_plan_generator
from .services.entity_resolver import (
    build_resolved_inline_entities_snippet,
    parse_inline_references,
)
from .services.history_analysis import analyze_completed_workouts_tool
from .services.macros_analysis import create_macros_analysis_tool
from .services.macros_manager import create_manage_macros_tool
from .services.mass_edit import (
    apply_applied_mass_edit_to_plan,
    create_applied_plan_mass_edit_tool,
    create_applied_plan_schedule_shift_tool,
    shift_applied_plan_schedule,
)
from .services.plan_analysis import create_plan_analysis_tool
from .services.simple_chat import simple_chat_generator
from .services.tool_agent import run_tools_agent
from .services.user_max_analysis import analyze_user_max_tool
from .tasks.mass_edit_tasks import execute_applied_mass_edit_task, execute_mass_edit_agent_task

configure_logging()
logger = structlog.get_logger(__name__)

app = FastAPI()

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

app.include_router(training_plans.router, prefix="/training-plans")
app.include_router(avatars.router, prefix="/avatars")
app.include_router(plan_mass_edit.router)


@app.get("/")
def read_root():
    return {"message": "Agent service is running"}


_firebase_request = requests.Request()
_firebase_project_id = os.getenv("FIREBASE_PROJECT_ID")


def _verify_firebase_token_sync(token: str) -> Optional[str]:
    """Verify a Firebase ID token and return the user_id (uid) or None."""
    if not token:
        return None
    try:
        claims = id_token.verify_firebase_token(token, _firebase_request)
        firebase_info = claims.get("firebase") or {}
        project_id = firebase_info.get("project_id")
        if _firebase_project_id and project_id and project_id != _firebase_project_id:
            print(
                f"[agent-service] Firebase token project_id mismatch: "
                f"got={project_id}, expected={_firebase_project_id}"
            )
            return None
        user_id = claims.get("uid") or claims.get("sub")
        if not user_id:
            return None
        return str(user_id)
    except Exception as exc:  # pragma: no cover - best-effort logging
        print(f"[agent-service] Firebase token verification failed: {exc}")
        return None


async def _verify_firebase_token(token: str) -> Optional[str]:
    """Async wrapper around _verify_firebase_token_sync for use in websocket."""
    return await asyncio.to_thread(_verify_firebase_token_sync, token)


async def _get_active_applied_plan_id(user_id: str) -> Optional[int]:
    """Fetch the user's active applied plan id from plans-service.

    Returns None if there is no active plan or the call fails.
    """

    base = settings.plans_service_url.rstrip("/")
    url = f"{base}/plans/applied-plans/active"
    headers = {"X-User-Id": user_id}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
        if resp.status_code == 404:
            logger.info("no_active_applied_plan", user_id=user_id)
            return None
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):
            plan_id = data.get("id")
            if isinstance(plan_id, int):
                return plan_id
        logger.warning("unexpected_active_plan_response", user_id=user_id, body=data)
    except Exception as exc:  # pragma: no cover - best-effort logging
        logger.error("failed_to_fetch_active_applied_plan", user_id=user_id, error=str(exc))
    return None


@app.websocket("/chat/ws")
async def chat_ws(websocket: WebSocket):
    # Verify Firebase token (query param 'token') using google-auth without firebase_admin
    token = websocket.query_params.get("token") or ""
    if not token:
        await websocket.close(code=4401)
        return
    user_id = await _verify_firebase_token(token)
    if not user_id:
        await websocket.close(code=4401)
        return
    await websocket.accept()
    session_id = str(uuid4())
    chat_state: Optional[Dict[str, Any]] = None
    fsm_state: Optional[Dict[str, Any]] = None
    session_context: Dict[str, Any] = {}  # Stores context v1 from frontend
    mode = "chat"
    await websocket.send_json({"type": "session_started", "session_id": session_id})
    try:
        while True:
            data = await websocket.receive_json()

            # Handle context payload from frontend (for auto-substitution)
            if data.get("type") == "context":
                session_context = data.get("payload") or {}
                logger.info(
                    "session_context_received",
                    session_id=session_id,
                    screen=session_context.get("screen"),
                    default_mass_edit_target=session_context.get("default_mass_edit_target"),
                )
                continue

            # Handle explicit apply of an existing applied-plan mass edit
            # using a previously generated JSON command (no extra LLM call).
            if data.get("type") == "mass_edit_apply":
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
                    continue

                raw_applied_plan_id = data.get("applied_plan_id")
                command = data.get("mass_edit_command") or data.get("command")

                try:
                    applied_plan_id = int(raw_applied_plan_id)
                except Exception:
                    await websocket.send_json(
                        {
                            "type": "message",
                            "role": "assistant",
                            "content": "Failed to apply changes: invalid applied_plan_id.",
                            "session_id": session_id,
                        }
                    )
                    continue

                if not isinstance(command, dict):
                    await websocket.send_json(
                        {
                            "type": "message",
                            "role": "assistant",
                            "content": "Failed to apply changes: invalid mass edit command payload.",
                            "session_id": session_id,
                        }
                    )
                    continue

                # Force mode="apply" while keeping the exact same filter/actions
                # structure that was used in preview.
                command["mode"] = "apply"

                try:
                    summary = await apply_applied_mass_edit_to_plan(
                        applied_plan_id=applied_plan_id,
                        user_id=user_id,
                        command=command,
                    )
                except Exception as exc:  # pragma: no cover - best-effort logging
                    logger.exception("applied_mass_edit_apply_from_preview_failed", exc_info=exc)
                    await websocket.send_json(
                        {
                            "type": "message",
                            "role": "assistant",
                            "content": "Не удалось применить изменения к активному плану.",
                            "session_id": session_id,
                        }
                    )
                    continue

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
                continue

            if data.get("type") == "schedule_shift_apply":
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
                    continue

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
                    continue

                if not isinstance(command, dict):
                    await websocket.send_json(
                        {
                            "type": "message",
                            "role": "assistant",
                            "content": "Failed to apply schedule shift: invalid command payload.",
                            "session_id": session_id,
                        }
                    )
                    continue

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
                    continue

                to_date_val = command.get("to_date")
                if to_date_val is not None:
                    to_date_val = str(to_date_val).strip() or None

                days_val = command.get("days", 0)
                try:
                    days = int(days_val)
                except Exception:
                    days = 0

                new_rest_days = command.get("new_rest_days")
                if new_rest_days is not None:
                    try:
                        new_rest_days = int(new_rest_days)
                    except Exception:
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
                    logger.exception("applied_schedule_shift_apply_from_preview_failed", exc_info=exc)
                    await websocket.send_json(
                        {
                            "type": "message",
                            "role": "assistant",
                            "content": "Не удалось применить сдвиг расписания активного плана.",
                            "session_id": session_id,
                        }
                    )
                    continue

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
                continue

            if data.get("type") == "message":
                content = str(data.get("content", ""))
                stripped = content.strip()

                # Slash-command for AI mass edit on the active applied plan.
                # Format: /mass-edit instructions
                if stripped.startswith("/mass-edit"):
                    rest = stripped[len("/mass-edit") :].strip()
                    if not rest:
                        await websocket.send_json(
                            {
                                "type": "message",
                                "role": "assistant",
                                "content": "Usage: /mass-edit <instructions>",
                                "session_id": session_id,
                            }
                        )
                        continue

                    instructions = rest
                    applied_plan_id = await _get_active_applied_plan_id(user_id)
                    if not applied_plan_id:
                        await websocket.send_json(
                            {
                                "type": "message",
                                "role": "assistant",
                                "content": (
                                    "No active applied plan found for this user. "
                                    "Please generate and apply a plan first."
                                ),
                                "session_id": session_id,
                            }
                        )
                        continue

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

                    previous_status = task.status
                    while True:
                        await asyncio.sleep(1.5)
                        async_result = AsyncResult(task.id, app=celery_app)
                        if async_result.status != previous_status:
                            previous_status = async_result.status
                            await websocket.send_json(
                                {
                                    "type": "mass_edit_task",
                                    "event": "progress",
                                    "task_id": task.id,
                                    "status": async_result.status,
                                    "session_id": session_id,
                                    "variant": "applied_plan",
                                }
                            )

                        if not async_result.ready():
                            continue

                        if async_result.failed():
                            await websocket.send_json(
                                {
                                    "type": "message",
                                    "role": "assistant",
                                    "content": f"Applied-plan mass edit failed: {async_result.result}",
                                    "session_id": session_id,
                                }
                            )
                            break

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
                        break

                    continue

                # Slash-command for AI mass edit
                # Supports context-based auto-substitution:
                #   - If context has default_mass_edit_target="applied", uses applied_plan_id
                #   - Formats (':' is optional):
                #       /mass_edit [mode]: instructions
                #       /mass_edit <plan_id> [mode]: instructions
                #       /mass_edit [mode] instructions
                #       /mass_edit <plan_id> [mode] instructions
                if stripped.startswith("/mass_edit"):
                    rest = stripped[len("/mass_edit") :].strip()
                    if not rest:
                        await websocket.send_json(
                            {
                                "type": "message",
                                "role": "assistant",
                                "content": "Usage: /mass_edit <plan_id> [mode]: <instructions>",
                                "session_id": session_id,
                            }
                        )
                        continue

                    # Check context for auto-substitution
                    ctx_target = session_context.get("default_mass_edit_target")
                    ctx_entities = session_context.get("entities") or {}
                    ctx_applied_plan = ctx_entities.get("active_applied_plan") or {}
                    ctx_applied_plan_id = ctx_applied_plan.get("id") if isinstance(ctx_applied_plan, dict) else None

                    # Split header / instructions if ':' is present, but ':' is optional
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
                    plan_id: Optional[int] = None
                    use_applied_plan = False

                    # Try to parse explicit plan_id / mode from tokens
                    if tokens:
                        first_token = tokens[0]
                        lower_first = first_token.lower()

                        # Try explicit plan_id (with or without ':')
                        plan_id_candidate: Optional[int] = None
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
                            # No explicit plan_id; maybe header only contains mode
                            if lower_first in {"apply", "preview"}:
                                mass_edit_mode = lower_first
                                if not instructions:
                                    instructions = " ".join(tokens[1:]).strip()
                            else:
                                # Context-based command without colon: treat whole rest as instructions
                                if not instructions:
                                    instructions = " ".join(tokens).strip()

                    # Auto-substitution from context if no explicit plan_id
                    if plan_id is None and ctx_target == "applied" and ctx_applied_plan_id:
                        use_applied_plan = True
                        logger.info(
                            "mass_edit_auto_substitution",
                            session_id=session_id,
                            applied_plan_id=ctx_applied_plan_id,
                            screen=session_context.get("screen"),
                        )
                    elif plan_id is None:
                        # No context and no explicit plan_id
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
                        continue

                    if not instructions:
                        await websocket.send_json(
                            {
                                "type": "message",
                                "role": "assistant",
                                "content": "Please provide instructions in /mass_edit.",
                                "session_id": session_id,
                            }
                        )
                        continue

                    # Execute appropriate task based on target
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

                    previous_status = task.status
                    task_variant = "applied_plan" if use_applied_plan else "calendar_plan"
                    while True:
                        await asyncio.sleep(1.5)
                        async_result = AsyncResult(task.id, app=celery_app)
                        if async_result.status != previous_status:
                            previous_status = async_result.status
                            await websocket.send_json(
                                {
                                    "type": "mass_edit_task",
                                    "event": "progress",
                                    "task_id": task.id,
                                    "status": async_result.status,
                                    "session_id": session_id,
                                }
                            )

                        if not async_result.ready():
                            continue

                        if async_result.failed():
                            await websocket.send_json(
                                {
                                    "type": "message",
                                    "role": "assistant",
                                    "content": f"Mass edit failed: {async_result.result}",
                                    "session_id": session_id,
                                }
                            )
                            break

                        payload = async_result.result or {}

                        # Different response based on variant
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
                        break

                    continue

                # FSM activation command
                if stripped == "@fsm_plan_generator":
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
                    continue

                # FSM mode: route messages to the plan generator
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
                    continue

                screen = session_context.get("screen")

                # For ActivePlanScreen and other key screens, route through tools-agent when tools are configured
                tools = []
                arguments_prompt: Optional[str] = None

                if screen == "active_plan":
                    # Build tools list (can be extended with more tools later)
                    tools = [
                        create_applied_plan_schedule_shift_tool(user_id),
                        create_applied_plan_mass_edit_tool(user_id),
                        create_plan_analysis_tool(user_id),
                    ]

                    # Extract minimal structured context for the agent
                    selection = session_context.get("selection") or {}
                    selection_date = selection.get("date")
                    entities = session_context.get("entities") or {}
                    active_applied_plan = entities.get("active_applied_plan") or {}
                    active_applied_plan_id = (
                        active_applied_plan.get("id") if isinstance(active_applied_plan, dict) else None
                    )

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
                    # Extract IDs from context if available
                    c_plan_id = session_context.get("calendar_plan_id")
                    a_plan_id = session_context.get("applied_plan_id")

                    tools = [
                        create_macros_analysis_tool(user_id),
                        create_manage_macros_tool(user_id),
                        create_plan_analysis_tool(user_id),
                    ]

                    # Provide IDs to the model so it knows what to pass to tools
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

                if tools and arguments_prompt:
                    try:
                        result = await run_tools_agent(
                            user_prompt=arguments_prompt,
                            tools=tools,
                            temperature=0.2,
                        )
                    except Exception as exc:
                        logger.exception("tools_agent_failed", exc_info=exc)
                        result = None

                    # If tool was called and returned summary, surface it; otherwise fall back to simple chat
                    if result and result.decision_type == "tool_call" and isinstance(result.tool_result, dict):
                        tool_res = result.tool_result
                        # Handle schedule shift summary
                        if result.tool_name == "applied_plan_schedule_shift":
                            summary = tool_res.get("summary") or {}
                            command = tool_res.get("schedule_shift_command") or {}
                            mode = tool_res.get("mode") or "apply"

                            workouts_shifted = summary.get("workouts_shifted")
                            days = summary.get("days")
                            msg = "Schedule shift applied."
                            if workouts_shifted is not None and days is not None:
                                msg = f"Shifted {workouts_shifted} workouts by {days} day(s)."

                            # Human-readable confirmation message
                            await websocket.send_json(
                                {
                                    "type": "message",
                                    "role": "assistant",
                                    "content": msg,
                                    "session_id": session_id,
                                }
                            )

                            # Structured payload for the frontend tool widget factory
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
                        # Handle mass edit summary
                        elif result.tool_name == "applied_plan_mass_edit":
                            summary = tool_res.get("summary") or {}
                            command = tool_res.get("mass_edit_command")
                            cmd_mode = None
                            if isinstance(command, dict):
                                cmd_mode = command.get("mode")

                            # Prefer explicit mode from summary, then from command,
                            # defaulting to "preview" for safety.
                            mode = summary.get("mode") or cmd_mode or "preview"

                            w_matched = summary.get("workouts_matched", 0)
                            sets_matched = summary.get("sets_matched", 0)
                            sets_modified = summary.get("sets_modified", 0)

                            if mode == "apply":
                                msg = f"Plan updated: {w_matched} workouts matched, " f"{sets_modified} sets modified."
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
                            # Send mass_edit_result event so the UI can render a
                            # structured preview/apply card (counts + filter/actions).
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
                        # Handle plan analysis
                        elif result.tool_name == "analyze_plan_progress":
                            summary_text = tool_res.get("summary", "")
                            recs = tool_res.get("recommendations", [])

                            msg_parts = [summary_text]
                            if recs:
                                msg_parts.append("\n**Recommendations:**")
                                for r in recs:
                                    msg_parts.append(f"- {r}")

                            await websocket.send_json(
                                {
                                    "type": "message",
                                    "role": "assistant",
                                    "content": "\n".join(msg_parts),
                                    "session_id": session_id,
                                }
                            )
                        # Handle macros analysis (list/definitions)
                        elif result.tool_name == "analyze_plan_macros":
                            data_str = json.dumps(tool_res, ensure_ascii=False)
                            prompt_context = (
                                "System: You are a fitness coach analyzing the automation "
                                "rules (macros) of a training plan. "
                                "You receive a JSON list of defined macros.\n\n"
                                f"Tool output (definitions):\n{data_str}\n\n"
                                f"User message: {content}\n\n"
                                "Instructions:\n"
                                "1) Explain simply what automation rules are present in this plan.\n"
                                "2) Describe the 'Trigger' (When it happens) and 'Action' "
                                "(What changes) for each rule in natural language.\n"
                                "3) Explain *why* such a rule might be useful (e.g. "
                                "auto-regulation for fatigue, progression logic).\n"
                                "4) If the list is empty, say there are no automation rules yet.\n"
                                "Answer in the same language as the user."
                            )

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
                        # Handle create/manage macros
                        elif result.tool_name == "create_manage_macros":
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
                        # Handle user max analysis
                        elif result.tool_name == "analyze_user_max_data":
                            data_str = json.dumps(tool_res, ensure_ascii=False)
                            prompt_context = (
                                "System: You are a strength coach inside WorkoutApp. "
                                "You receive JSON with aggregated strength analytics for this user "
                                "from the backend. "
                                "Use it to give a short, concrete explanation.\n\n"
                                f"Tool output (analyze_user_max_data):\n{data_str}\n\n"
                                f"User message: {content}\n\n"
                                "Instructions:\n"
                                "1) Briefly list the 1–3 weakest muscle groups and why "
                                "(use z-score, trend, and priority_reason if present).\n"
                                "2) If 'anomaly_details' is present, for each anomaly mention "
                                "the concrete exercise, weight and reps "
                                "(for example: 'Bench press 120 kg x 5') and explain in one "
                                "sentence why this looks anomalous "
                                "(sudden jump vs neighbours, inconsistent with trend, etc.).\n"
                                "3) Avoid vague phrases like 'anomaly on day 2' or bare indices. "
                                "Always tie anomalies to exercises and loads.\n"
                                "4) Finish with 1–3 practical suggestions for what the user can do next.\n"
                                "Answer in the same language that the user used in their message."
                            )

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
                        # Handle completed workouts analysis
                        elif result.tool_name == "analyze_completed_workouts":
                            data_str = json.dumps(tool_res, ensure_ascii=False)
                            prompt_context = (
                                "System: You are a strength coach inside WorkoutApp. "
                                "You receive JSON with user's completed workout history analysis. "
                                "Use it to give a summary of their training consistency, frequency, "
                                "and volume trends.\n\n"
                                f"Tool output (analyze_completed_workouts):\n{data_str}\n\n"
                                f"User message: {content}\n\n"
                                "Instructions:\n"
                                "1) Summarize their consistency (workouts per week).\n"
                                "2) Comment on volume/intensity trends if visible.\n"
                                "3) Give a short encouraging remark or advice based on the data.\n"
                                "Answer in the same language that the user used in their message."
                            )

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
                        else:
                            # Fallback for unknown tool
                            await websocket.send_json(
                                {
                                    "type": "message",
                                    "role": "assistant",
                                    "content": "Action completed.",
                                    "session_id": session_id,
                                }
                            )
                        continue

                # Default behaviour (or fallback): plain chat via simple GPT wrapper
                system_prompt_for_screen = None
                if screen == "plan_details":
                    system_prompt_for_screen = (
                        "You are an assistant inside WorkoutApp on the Plan Details screen. "
                        "Here the word 'macros' refers to training plan macros "
                        "(automation rules for the training plan), not nutrition macros "
                        "like proteins, fats, or carbs, unless the user explicitly asks "
                        "about food or diet."
                    )
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
            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong", "session_id": session_id})
    except WebSocketDisconnect:
        pass


@app.websocket("/chat/simple")
async def simple_chat_ws(websocket: WebSocket):
    token = websocket.query_params.get("token") or ""
    if not token:
        await websocket.close(code=4401)
        return
    user_id = await _verify_firebase_token(token)
    if not user_id:
        await websocket.close(code=4401)
        return

    system_prompt = websocket.query_params.get("prompt")

    await websocket.accept()
    session_id = str(uuid4())
    chat_state: Optional[Dict[str, Any]] = None
    await websocket.send_json({"type": "session_started", "session_id": session_id})

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            if msg_type == "message":
                content = str(data.get("content", ""))
                result = await simple_chat_generator(
                    content,
                    state=chat_state,
                    user_id=user_id,
                    system_prompt=system_prompt,
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
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong", "session_id": session_id})
    except WebSocketDisconnect:
        pass
