import asyncio
import os
from typing import Optional
from uuid import uuid4

import structlog
from celery.result import AsyncResult
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from google.auth.transport import requests
from google.oauth2 import id_token
from prometheus_fastapi_instrumentator import Instrumentator

from .celery_app import celery_app
from .logging_config import configure_logging
from .routers import avatars, plan_mass_edit, training_plans
from .services.conversation_graph import ConversationGraph
from .tasks.mass_edit_tasks import execute_mass_edit_agent_task

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
    graph = ConversationGraph(user_id=user_id)
    await websocket.send_json({"type": "session_started", "session_id": session_id})
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "message":
                content = str(data.get("content", ""))

                # Slash-command for AI mass edit that bypasses the conversation graph
                # Format: /mass_edit <plan_id> [mode]: instructions
                stripped = content.strip()
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

                    if ":" in rest:
                        header, instructions = rest.split(":", 1)
                        instructions = instructions.strip()
                    else:
                        header, instructions = rest, ""

                    parts = [p for p in header.split(" ") if p]
                    if not parts:
                        await websocket.send_json(
                            {
                                "type": "message",
                                "role": "assistant",
                                "content": (
                                    "Could not parse plan_id. Usage: /mass_edit <plan_id> [mode]: " "<instructions>"
                                ),
                                "session_id": session_id,
                            }
                        )
                        continue

                    plan_id_str = parts[0]
                    mode = parts[1].lower() if len(parts) >= 2 else "apply"

                    try:
                        plan_id = int(plan_id_str)
                    except Exception:
                        await websocket.send_json(
                            {
                                "type": "message",
                                "role": "assistant",
                                "content": (
                                    "plan_id must be an integer. Usage: /mass_edit <plan_id> [mode]: " "<instructions>"
                                ),
                                "session_id": session_id,
                            }
                        )
                        continue

                    if mode not in {"preview", "apply"}:
                        mode = "apply"

                    if not instructions:
                        await websocket.send_json(
                            {
                                "type": "message",
                                "role": "assistant",
                                "content": "Please provide instructions after the ':' in /mass_edit.",
                                "session_id": session_id,
                            }
                        )
                        continue

                    task = execute_mass_edit_agent_task.delay(
                        plan_id=plan_id,
                        user_id=user_id,
                        mode=mode,
                        prompt=instructions,
                    )

                    await websocket.send_json(
                        {
                            "type": "mass_edit_task",
                            "event": "submitted",
                            "task_id": task.id,
                            "status": task.status,
                            "session_id": session_id,
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

                # Default behaviour: send message through the ConversationGraph
                reply, done = await graph.process_response(content)
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
            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong", "session_id": session_id})
    except WebSocketDisconnect:
        pass
