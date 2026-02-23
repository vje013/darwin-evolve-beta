"""
Darwin Enterprise Evolve Beta — WebSocket Manager
Tracks active connections per room. Broadcasts messages in real-time.
"""
import json
from fastapi import WebSocket
from collections import defaultdict


class ConnectionManager:
    """Manages WebSocket connections per room."""

    def __init__(self):
        # room_id -> list of (websocket, user_id, display_name)
        self.active_connections: dict[str, list[tuple[WebSocket, str, str]]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, room_id: str, user_id: str, display_name: str):
        await websocket.accept()
        self.active_connections[room_id].append((websocket, user_id, display_name))

    def disconnect(self, websocket: WebSocket, room_id: str):
        self.active_connections[room_id] = [
            (ws, uid, name) for ws, uid, name in self.active_connections[room_id]
            if ws != websocket
        ]
        if not self.active_connections[room_id]:
            del self.active_connections[room_id]

    async def broadcast_to_room(self, room_id: str, message: dict, exclude_user_id: str | None = None):
        """Send a message to all connected clients in a room, optionally excluding the sender."""
        if room_id not in self.active_connections:
            return

        dead_connections = []
        payload = json.dumps(message)

        for ws, uid, name in self.active_connections[room_id]:
            if exclude_user_id and uid == exclude_user_id:
                continue
            try:
                await ws.send_text(payload)
            except Exception:
                dead_connections.append(ws)

        # Clean up dead connections
        for ws in dead_connections:
            self.disconnect(ws, room_id)

    def get_online_users(self, room_id: str) -> list[dict]:
        """Get list of currently online users in a room."""
        if room_id not in self.active_connections:
            return []
        seen = set()
        users = []
        for _, uid, name in self.active_connections[room_id]:
            if uid not in seen:
                seen.add(uid)
                users.append({"user_id": uid, "display_name": name})
        return users


# Singleton instance
manager = ConnectionManager()
