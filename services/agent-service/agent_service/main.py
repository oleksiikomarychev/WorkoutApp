from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from uuid import uuid4
from .services.conversation_graph import ConversationGraph
from .routers import training_plans, avatars

app = FastAPI()

app.include_router(training_plans.router, prefix="/training-plans")
app.include_router(avatars.router, prefix="/avatars")

@app.get("/")
def read_root():
    return {"message": "Agent service is running"}

@app.websocket("/chat/ws")
async def chat_ws(websocket: WebSocket):
    await websocket.accept()
    session_id = str(uuid4())
    graph = ConversationGraph()
    await websocket.send_json({"type": "session_started", "session_id": session_id})
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "message":
                content = data.get("content", "")
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