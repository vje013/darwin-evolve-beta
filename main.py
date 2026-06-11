"""
Darwin Enterprise Evolve Beta — Main Application
FastAPI server with WebSocket support, SQLite + Neo4j, OpenRouter LLM gateway.

Start with: uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from routes.training import router as training_router
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware

from db import init_db, get_db
from services.graph import init_graph, close_driver
from services.ws_manager import manager
from auth import (
    RegisterRequest, LoginRequest, TokenResponse,
    register_user, login_user, get_current_user, decode_token, check_room_access
)
from fastapi import Depends

from routes.rooms import router as rooms_router
from routes.messages import router as messages_router
from routes.artifacts import router as artifacts_router
from routes.connectors import router as connectors_router
from routes.clinic_agent import router as clinic_router
from routes.research_agent import router as research_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize databases on startup, cleanup on shutdown."""
    print("🚀 Darwin Enterprise Evolve Beta starting...")
    init_db()
    try:
        init_graph()
    except Exception as e:
        print(f"⚠ Neo4j not available yet: {e}")
        print("  Run 'docker-compose up' to start Neo4j")
    yield
    close_driver()
    print("👋 Shutting down")


app = FastAPI(
    title="Darwin Enterprise Evolve Beta",
    description="Collaborative AI chat with graph-backed traceability",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Auth Routes (top-level) ---

@app.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest):
    return register_user(req)


@app.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    return login_user(req)


@app.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "display_name": user["display_name"],
        "created_at": user["created_at"],
    }


# --- Health Check ---

@app.get("/health")
async def health():
    from services.graph import get_driver
    neo4j_ok = False
    try:
        driver = get_driver()
        with driver.session() as session:
            session.run("RETURN 1")
        neo4j_ok = True
    except Exception:
        pass

    db_ok = False
    try:
        from db import get_db
        with get_db() as conn:
            conn.execute("SELECT 1")
        db_ok = True
    except Exception:
        pass

    return {
        "status": "ok" if (neo4j_ok and db_ok) else "degraded",
        "neo4j": "connected" if neo4j_ok else "disconnected",
        "sqlite": "connected" if db_ok else "disconnected",
        "version": "0.1.0",
    }


# --- Mount Routers ---

app.include_router(rooms_router)
app.include_router(messages_router)
app.include_router(artifacts_router)
app.include_router(connectors_router)
app.include_router(training_router)
app.include_router(clinic_router)
app.include_router(research_router)


# --- WebSocket for Real-Time Chat ---

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: str,
    token: str = Query(default=""),
):
    """
    WebSocket connection for real-time room messages.
    Connect with: ws://localhost:8000/ws/{room_id}?token={jwt}
    """
    # Authenticate via token query param
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    try:
        user_id = decode_token(token)
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return

    # Verify room access
    try:
        check_room_access(user_id, room_id, "viewer")
    except Exception:
        await websocket.close(code=4003, reason="No access to room")
        return

    # Get display name
    with get_db() as conn:
        row = conn.execute("SELECT display_name FROM users WHERE user_id = ?", (user_id,)).fetchone()
        display_name = row["display_name"] if row else "Unknown"

    # Connect
    await manager.connect(websocket, room_id, user_id, display_name)

    # Notify room that user came online
    await manager.broadcast_to_room(room_id, {
        "type": "user_joined",
        "user_id": user_id,
        "display_name": display_name,
        "online_users": manager.get_online_users(room_id),
    }, exclude_user_id=user_id)

    try:
        while True:
            # Keep connection alive — listen for pings or client messages
            data = await websocket.receive_text()
            # Client can send ping to keep alive
            if data == "ping":
                await websocket.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
        await manager.broadcast_to_room(room_id, {
            "type": "user_left",
            "user_id": user_id,
            "display_name": display_name,
            "online_users": manager.get_online_users(room_id),
        })


# --- Spend Dashboard (simple) ---

@app.get("/spend")
async def get_spend(user: dict = Depends(get_current_user)):
    """Global spend across all rooms the user has access to."""
    from db import get_db
    with get_db() as conn:
        rows = conn.execute("""
            SELECT mi.room_id, r.name AS room_name, mi.model,
                   SUM(mi.cost) AS total_cost,
                   SUM(mi.tokens_in + mi.tokens_out) AS total_tokens,
                   COUNT(*) AS invocations
            FROM model_invocations mi
            JOIN rooms r ON mi.room_id = r.room_id
            JOIN room_members rm ON mi.room_id = rm.room_id AND rm.user_id = ?
            GROUP BY mi.room_id, mi.model
            ORDER BY total_cost DESC
        """, (user["user_id"],)).fetchall()

    return [dict(r) for r in rows]
