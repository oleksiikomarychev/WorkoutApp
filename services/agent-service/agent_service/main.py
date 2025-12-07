import asyncio
import os
from typing import Any
from uuid import uuid4

import httpx
import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from google.auth.transport import requests
from google.oauth2 import id_token
from prometheus_fastapi_instrumentator import Instrumentator

from .config import settings
from .logging_config import configure_logging
from .routers import avatars, plan_mass_edit, training_plans
from .services.event_dispatcher import EventDispatcher
from .services.simple_chat import simple_chat_generator

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


def _verify_firebase_token_sync(token: str) -> str | None:
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


async def _verify_firebase_token(token: str) -> str | None:
    return await asyncio.to_thread(_verify_firebase_token_sync, token)


async def _get_active_applied_plan_id(user_id: str) -> int | None:
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


event_dispatcher = EventDispatcher(logger=logger, get_active_applied_plan_id=_get_active_applied_plan_id)


@app.websocket("/chat/ws")
async def chat_ws(websocket: WebSocket):
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
    chat_state: dict[str, Any] | None = None
    fsm_state: dict[str, Any] | None = None
    session_context: dict[str, Any] = {}
    mode = "chat"
    await websocket.send_json({"type": "session_started", "session_id": session_id})
    try:
        while True:
            data = await websocket.receive_json()
            chat_state, fsm_state, session_context, mode, handled = await event_dispatcher.dispatch(
                data=data,
                websocket=websocket,
                session_id=session_id,
                user_id=user_id,
                chat_state=chat_state,
                fsm_state=fsm_state,
                session_context=session_context,
                mode=mode,
            )
            if handled:
                continue
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
    chat_state: dict[str, Any] | None = None
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
