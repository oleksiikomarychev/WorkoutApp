from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import os
import asyncio
from typing import Optional
from uuid import uuid4

from google.oauth2 import id_token
from google.auth.transport import requests

from .services.conversation_graph import ConversationGraph
from .services.mass_edit import create_plan_mass_edit_tool
from .services.tool_agent import run_tools_agent
from .routers import training_plans, avatars, plan_mass_edit

app = FastAPI()

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
                    rest = stripped[len("/mass_edit"):].strip()
                    if not rest:
                        await websocket.send_json({
                            "type": "message",
                            "role": "assistant",
                            "content": "Usage: /mass_edit <plan_id> [mode]: <instructions>",
                            "session_id": session_id,
                        })
                        continue

                    if ":" in rest:
                        header, instructions = rest.split(":", 1)
                        instructions = instructions.strip()
                    else:
                        header, instructions = rest, ""

                    parts = [p for p in header.split(" ") if p]
                    if not parts:
                        await websocket.send_json({
                            "type": "message",
                            "role": "assistant",
                            "content": "Could not parse plan_id. Usage: /mass_edit <plan_id> [mode]: <instructions>",
                            "session_id": session_id,
                        })
                        continue

                    plan_id_str = parts[0]
                    mode = parts[1].lower() if len(parts) >= 2 else "apply"

                    try:
                        plan_id = int(plan_id_str)
                    except Exception:
                        await websocket.send_json({
                            "type": "message",
                            "role": "assistant",
                            "content": "plan_id must be an integer. Usage: /mass_edit <plan_id> [mode]: <instructions>",
                            "session_id": session_id,
                        })
                        continue

                    if mode not in {"preview", "apply"}:
                        mode = "apply"

                    if not instructions:
                        await websocket.send_json({
                            "type": "message",
                            "role": "assistant",
                            "content": "Please provide instructions after the ':' in /mass_edit.",
                            "session_id": session_id,
                        })
                        continue

                    tool = create_plan_mass_edit_tool(user_id)
                    arguments_prompt = (
                        f"You must use the `plan_mass_edit` tool if it helps. "
                        f"The target plan_id is {plan_id} and default mode is {mode}. "
                        f"User instructions: {instructions}"
                    )

                    result = await run_tools_agent(
                        user_prompt=arguments_prompt,
                        tools=[tool],
                        temperature=0.2,
                    )

                    reply_text = result.answer
                    if not reply_text:
                        if result.decision_type == "tool_call" and isinstance(result.tool_result, dict):
                            reply_text = "AI mass edit has been applied to your plan."
                        elif result.decision_type == "answer":
                            reply_text = "AI responded, but no text answer was returned."
                        else:
                            reply_text = "AI could not process the mass edit request."

                    await websocket.send_json({
                        "type": "message",
                        "role": "assistant",
                        "content": reply_text,
                        "session_id": session_id,
                    })

                    if result.decision_type == "tool_call" and isinstance(result.tool_result, dict):
                        await websocket.send_json({
                            "type": "message",
                            "role": "assistant",
                            "content": "(Internal) plan and mass edit command have been updated on the server side.",
                            "session_id": session_id,
                        })

                    continue

                # Default behaviour: send message through the ConversationGraph
                reply, done = await graph.process_response(content)
                if reply:
                    await websocket.send_json({
                        "type": "message",
                        "role": "assistant",
                        "content": reply,
                        "session_id": session_id
                    })
                if done:
                    await websocket.send_json({"type": "done", "session_id": session_id})
            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong", "session_id": session_id})
    except WebSocketDisconnect:
        pass