"""
Darwin Enterprise Evolve Beta — Room Routes
Room CRUD, member management, settings, model selection.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user, check_room_access
from db import get_db
from services.graph import create_room_node
from services.audit import audit
from services.llm import AVAILABLE_MODELS

import httpx
import time as _time

router = APIRouter(prefix="/rooms", tags=["rooms"])

_models_cache = {"data": None, "fetched_at": 0}

@router.get("/models/live")
async def get_live_models(user: dict = Depends(get_current_user)):
    """Fetch available models from OpenRouter with 24hr cache."""
    now = _time.time()
    if _models_cache["data"] and (now - _models_cache["fetched_at"]) < 86400:
        return _models_cache["data"]

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.get("https://openrouter.ai/api/v1/models")
            if res.status_code != 200:
                raise Exception(f"OpenRouter returned {res.status_code}")
            all_models = res.json().get("data", [])

        # Filter to models we support
        supported_prefixes = [
            "anthropic/claude-sonnet-4",
            "anthropic/claude-3.5-haiku",
            "anthropic/claude-3.5-sonnet",
            "anthropic/claude-3.7-sonnet",
            "openai/gpt-4o-mini",
            "openai/gpt-4o",
            "google/gemini-2.0-flash",
            "google/gemini-2.0-pro",
        ]

        filtered = []
        for m in all_models:
            mid = m.get("id", "")
            if any(mid.startswith(p) for p in supported_prefixes):
                filtered.append({
                    "id": mid,
                    "name": m.get("name", mid),
                    "description": m.get("description", ""),
                    "context_length": m.get("context_length", 0),
                    "pricing": {
                        "prompt": m.get("pricing", {}).get("prompt", "0"),
                        "completion": m.get("pricing", {}).get("completion", "0"),
                    },
                    "provider": mid.split("/")[0] if "/" in mid else "",
                })

        _models_cache["data"] = filtered
        _models_cache["fetched_at"] = now
        return filtered

    except Exception as e:
        # Fallback to hardcoded if OpenRouter is down
        return [
            {"id": "anthropic/claude-sonnet-4", "name": "Claude Sonnet", "description": "", "context_length": 200000, "pricing": {"prompt": "3.0", "completion": "15.0"}, "provider": "anthropic"},
            {"id": "anthropic/claude-3.5-haiku", "name": "Claude Haiku", "description": "", "context_length": 200000, "pricing": {"prompt": "0.8", "completion": "4.0"}, "provider": "anthropic"},
            {"id": "openai/gpt-4o", "name": "GPT-4o", "description": "", "context_length": 128000, "pricing": {"prompt": "2.5", "completion": "10.0"}, "provider": "openai"},
            {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "description": "", "context_length": 128000, "pricing": {"prompt": "0.15", "completion": "0.6"}, "provider": "openai"},
            {"id": "google/gemini-2.0-flash-001", "name": "Gemini Flash", "description": "", "context_length": 1000000, "pricing": {"prompt": "0.1", "completion": "0.4"}, "provider": "google"},
        ]

# --- Request/Response Models ---

class CreateRoomRequest(BaseModel):
    name: str
    description: str = ""
    default_model: str = "anthropic/claude-sonnet-4"


class UpdateRoomSettings(BaseModel):
    name: str | None = None
    description: str | None = None
    default_model: str | None = None
    budget_cap_monthly: float | None = None
    strict_citations: bool | None = None


class AddMemberRequest(BaseModel):
    email: str
    role: str = "member"


class UpdateMemberRole(BaseModel):
    role: str


# --- Room CRUD ---

@router.post("")
async def create_room(req: CreateRoomRequest, user: dict = Depends(get_current_user)):
    room_id = str(uuid.uuid4())
    user_id = user["user_id"]

    with get_db() as conn:
        conn.execute(
            "INSERT INTO rooms (room_id, name, description, default_model, created_by) VALUES (?, ?, ?, ?, ?)",
            (room_id, req.name, req.description, req.default_model, user_id)
        )
        # Creator is automatically owner
        conn.execute(
            "INSERT INTO room_members (room_id, user_id, role) VALUES (?, ?, 'owner')",
            (room_id, user_id)
        )

    # Mirror to graph
    create_room_node(room_id, req.name, user_id)

    # Audit
    audit(user_id, "room_created", room_id, "room", room_id, {"name": req.name, "model": req.default_model})

    return {"room_id": room_id, "name": req.name, "default_model": req.default_model}


@router.get("")
async def list_rooms(user: dict = Depends(get_current_user)):
    user_id = user["user_id"]
    with get_db() as conn:
        rows = conn.execute("""
            SELECT r.room_id, r.name, r.description, r.default_model, r.created_at,
                   rm.role,
                   (SELECT COUNT(*) FROM room_members WHERE room_id = r.room_id) AS member_count
            FROM rooms r
            JOIN room_members rm ON r.room_id = rm.room_id AND rm.user_id = ?
            ORDER BY r.created_at DESC
        """, (user_id,)).fetchall()
    return [dict(r) for r in rows]


@router.get("/models")
async def list_models():
    """Return available models for the model selector UI."""
    return AVAILABLE_MODELS


@router.get("/{room_id}")
async def get_room(room_id: str, user: dict = Depends(get_current_user)):
    check_room_access(user["user_id"], room_id, "viewer")

    with get_db() as conn:
        room = conn.execute("SELECT * FROM rooms WHERE room_id = ?", (room_id,)).fetchone()
        if not room:
            raise HTTPException(404, "Room not found")

        members = conn.execute("""
            SELECT u.user_id, u.email, u.display_name, rm.role, rm.joined_at
            FROM room_members rm
            JOIN users u ON rm.user_id = u.user_id
            WHERE rm.room_id = ?
        """, (room_id,)).fetchall()

        # Spend summary
        spend = conn.execute("""
            SELECT COALESCE(SUM(cost), 0) AS total_cost,
                   COALESCE(SUM(tokens_in + tokens_out), 0) AS total_tokens,
                   COUNT(*) AS invocation_count
            FROM model_invocations
            WHERE room_id = ?
        """, (room_id,)).fetchone()

    return {
        **dict(room),
        "members": [dict(m) for m in members],
        "spend": dict(spend),
    }


@router.put("/{room_id}/settings")
async def update_room_settings(room_id: str, req: UpdateRoomSettings, user: dict = Depends(get_current_user)):
    check_room_access(user["user_id"], room_id, "admin")

    updates = {}
    if req.name is not None:
        updates["name"] = req.name
    if req.description is not None:
        updates["description"] = req.description
    if req.default_model is not None:
        updates["default_model"] = req.default_model
    if req.budget_cap_monthly is not None:
        updates["budget_cap_monthly"] = req.budget_cap_monthly
    if req.strict_citations is not None:
        updates["strict_citations"] = 1 if req.strict_citations else 0

    if not updates:
        raise HTTPException(400, "No fields to update")

    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values()) + [room_id]

    with get_db() as conn:
        conn.execute(f"UPDATE rooms SET {set_clause} WHERE room_id = ?", values)

    audit(user["user_id"], "room_settings_updated", room_id, "room", room_id, updates)

    return {"updated": updates}


# --- Member Management ---

@router.get("/{room_id}/members")
async def list_members(room_id: str, user: dict = Depends(get_current_user)):
    check_room_access(user["user_id"], room_id, "viewer")

    with get_db() as conn:
        members = conn.execute("""
            SELECT u.user_id, u.email, u.display_name, rm.role, rm.joined_at
            FROM room_members rm
            JOIN users u ON rm.user_id = u.user_id
            WHERE rm.room_id = ?
        """, (room_id,)).fetchall()

    return [dict(m) for m in members]


@router.post("/{room_id}/members")
async def add_member(room_id: str, req: AddMemberRequest, user: dict = Depends(get_current_user)):
    check_room_access(user["user_id"], room_id, "admin")

    if req.role not in ("member", "admin", "viewer"):
        raise HTTPException(400, "Invalid role. Use: member, admin, or viewer")

    with get_db() as conn:
        # Find user by email
        target = conn.execute("SELECT user_id FROM users WHERE email = ?", (req.email,)).fetchone()
        if not target:
            raise HTTPException(404, "User not found with that email")

        # Check if already a member
        existing = conn.execute(
            "SELECT role FROM room_members WHERE room_id = ? AND user_id = ?",
            (room_id, target["user_id"])
        ).fetchone()
        if existing:
            raise HTTPException(409, f"User is already a {existing['role']} in this room")

        conn.execute(
            "INSERT INTO room_members (room_id, user_id, role) VALUES (?, ?, ?)",
            (room_id, target["user_id"], req.role)
        )

    audit(user["user_id"], "member_added", room_id, "user", target["user_id"], {"role": req.role})

    return {"user_id": target["user_id"], "role": req.role}


@router.put("/{room_id}/members/{target_user_id}")
async def update_member_role(room_id: str, target_user_id: str, req: UpdateMemberRole, user: dict = Depends(get_current_user)):
    check_room_access(user["user_id"], room_id, "owner")

    if req.role not in ("member", "admin", "viewer"):
        raise HTTPException(400, "Invalid role")

    with get_db() as conn:
        result = conn.execute(
            "UPDATE room_members SET role = ? WHERE room_id = ? AND user_id = ?",
            (req.role, room_id, target_user_id)
        )
        if result.rowcount == 0:
            raise HTTPException(404, "Member not found")

    audit(user["user_id"], "role_changed", room_id, "user", target_user_id, {"new_role": req.role})

    return {"user_id": target_user_id, "role": req.role}


@router.delete("/{room_id}/members/{target_user_id}")
async def remove_member(room_id: str, target_user_id: str, user: dict = Depends(get_current_user)):
    check_room_access(user["user_id"], room_id, "admin")

    # Can't remove yourself if you're the owner
    if target_user_id == user["user_id"]:
        raise HTTPException(400, "Cannot remove yourself. Transfer ownership first.")

    with get_db() as conn:
        result = conn.execute(
            "DELETE FROM room_members WHERE room_id = ? AND user_id = ?",
            (room_id, target_user_id)
        )
        if result.rowcount == 0:
            raise HTTPException(404, "Member not found")

    audit(user["user_id"], "member_removed", room_id, "user", target_user_id)

    return {"removed": target_user_id}