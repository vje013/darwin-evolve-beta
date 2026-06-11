"""
Darwin Enterprise Evolve Beta — Auth
Simple JWT auth with role-based room ACLs.
The system — not the LLM — enforces access.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Depends, Request
from jose import jwt, JWTError
import bcrypt
from pydantic import BaseModel, EmailStr

from db import get_db
from services.graph import create_user_node, write_audit_event

JWT_SECRET = os.getenv("JWT_SECRET", "change-this-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))


ROLE_HIERARCHY = {"viewer": 0, "member": 1, "admin": 2, "owner": 3}


# --- Pydantic Models ---

class RegisterRequest(BaseModel):
    email: str
    display_name: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    display_name: str


class UserOut(BaseModel):
    user_id: str
    email: str
    display_name: str
    created_at: str


# --- Token Operations ---

def create_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user_id, "exp": expire},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )


def decode_token(token: str) -> str:
    """Returns user_id or raises."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(401, "Invalid token")
        return user_id
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")


# --- Auth Dependency ---

async def get_current_user(request: Request) -> dict:
    """FastAPI dependency: extracts and validates JWT from Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")

    token = auth_header.split(" ")[1]
    user_id = decode_token(token)

    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            raise HTTPException(401, "User not found")
        return dict(row)


# --- Room ACL ---

def check_room_access(user_id: str, room_id: str, required_role: str = "member"):
    """Enforce room-level access control. Raises 403 if insufficient."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT role FROM room_members WHERE room_id = ? AND user_id = ?",
            (room_id, user_id)
        ).fetchone()

        if not row:
            raise HTTPException(403, "Not a member of this room")

        if ROLE_HIERARCHY.get(row["role"], 0) < ROLE_HIERARCHY.get(required_role, 0):
            raise HTTPException(403, f"Requires {required_role} role or higher")

    return row["role"]


# --- Registration & Login ---

def register_user(req: RegisterRequest) -> TokenResponse:
    user_id = str(uuid.uuid4())

    with get_db() as conn:
        # Check for existing email
        existing = conn.execute("SELECT user_id FROM users WHERE email = ?", (req.email,)).fetchone()
        if existing:
            raise HTTPException(409, "Email already registered")

        password_hash = bcrypt.hashpw(req.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        conn.execute(
            "INSERT INTO users (user_id, email, display_name, password_hash) VALUES (?, ?, ?, ?)",
            (user_id, req.email, req.display_name, password_hash)
        )

    # Mirror to graph
    create_user_node(user_id, req.email, req.display_name)

    # Audit
    write_audit_event(
        audit_id=str(uuid.uuid4()),
        user_id=user_id,
        room_id=None,
        action="user_registered",
        target_type="user",
        target_id=user_id,
        metadata={"email": req.email}
    )

    token = create_token(user_id)
    return TokenResponse(access_token=token, user_id=user_id, display_name=req.display_name)


def login_user(req: LoginRequest) -> TokenResponse:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (req.email,)).fetchone()
        if not row:
            raise HTTPException(401, "Invalid email or password")

        if not bcrypt.checkpw(req.password.encode('utf-8'), row["password_hash"].encode('utf-8')):
            raise HTTPException(401, "Invalid email or password")

    token = create_token(row["user_id"])
    return TokenResponse(
        access_token=token,
        user_id=row["user_id"],
        display_name=row["display_name"]
    )
