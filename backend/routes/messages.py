"""
Darwin Enterprise Evolve Beta — Message Routes
Chat messages, @bachman detection, AI responses with context, entity extraction.
WebSocket broadcasting for real-time multi-user chat.
"""
import re
import uuid
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user, check_room_access
from db import get_db
from services.llm import call_llm
from services.graph import get_room_context, get_recent_decisions, get_file_contents
from services.extractor import extract_entities_from_conversation
from services.audit import audit
from services.ws_manager import manager

router = APIRouter(prefix="/rooms/{room_id}/messages", tags=["messages"])

BACHMAN_MENTION = re.compile(r"@bachman\b", re.IGNORECASE)

AI_SYSTEM_PROMPT = """You are a collaborative AI participant in a team chat room for Darwin Enterprise Evolve.
You are embedded in the conversation as a teammate, not as an external tool.

Your capabilities:
- Answer questions about requirements, designs, decisions, PRs, and tasks
- Propose solutions, interaction states, edge cases, and architectures
- Reference specific artifacts when you have context about them
- Help with traceability: connecting requirements → designs → code → tests

When you have graph context about linked entities, cite them by name.
Format citations as [Entity Name] so they can be linked.

Be concise, technical, and direct. This is a working chat, not a support ticket.
If you reference a prior decision, say so: "Per the decision on [date]: ..."
If you notice potential drift (design changed but code didn't), flag it."""


class SendMessageRequest(BaseModel):
    content: str
    thread_id: str | None = None
    model_override: str | None = None

    model_config = {"protected_namespaces": ()}


class MessageOut(BaseModel):
    message_id: str
    room_id: str
    author_id: str
    author_type: str
    author_name: str
    content: str
    thread_id: str | None
    model_used: str | None
    created_at: str

    model_config = {"protected_namespaces": ()}


@router.get("")
async def get_messages(
    room_id: str,
    limit: int = 50,
    before: str | None = None,
    thread_id: str | None = None,
    user: dict = Depends(get_current_user),
):
    check_room_access(user["user_id"], room_id, "viewer")

    with get_db() as conn:
        query = """
            SELECT m.*, u.display_name AS author_name
            FROM messages m
            LEFT JOIN users u ON m.author_id = u.user_id
            WHERE m.room_id = ?
        """
        params = [room_id]

        if thread_id:
            query += " AND (m.thread_id = ? OR m.message_id = ?)"
            params.extend([thread_id, thread_id])

        if before:
            query += " AND m.created_at < ?"
            params.append(before)

        query += " ORDER BY m.created_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()

    messages = [dict(r) for r in reversed(rows)]
    for m in messages:
        if m["author_type"] == "ai":
            m["author_name"] = "Bachman"
        elif m["author_type"] == "system":
            m["author_name"] = "System"
        elif not m.get("author_name"):
            m["author_name"] = "Unknown"

    return messages


@router.post("")
async def send_message(
    room_id: str,
    req: SendMessageRequest,
    user: dict = Depends(get_current_user),
):
    check_room_access(user["user_id"], room_id, "member")

    user_id = user["user_id"]
    message_id = str(uuid.uuid4())
    created_at = None

    with get_db() as conn:
        conn.execute(
            """INSERT INTO messages (message_id, room_id, author_id, author_type, content, thread_id)
               VALUES (?, ?, ?, 'human', ?, ?)""",
            (message_id, room_id, user_id, req.content, req.thread_id)
        )
        row = conn.execute("SELECT created_at FROM messages WHERE message_id = ?", (message_id,)).fetchone()
        created_at = row["created_at"] if row else None

    audit(user_id, "message_sent", room_id, "message", message_id)

    human_msg = {
        "type": "message",
        "message_id": message_id,
        "room_id": room_id,
        "author_id": user_id,
        "author_type": "human",
        "author_name": user["display_name"],
        "content": req.content,
        "thread_id": req.thread_id,
        "model_used": None,
        "created_at": created_at,
    }

    await manager.broadcast_to_room(room_id, human_msg, exclude_user_id=user_id)

    response_data = {
        **human_msg,
        "ai_response": None,
    }

    if BACHMAN_MENTION.search(req.content):
        await manager.broadcast_to_room(room_id, {
            "type": "ai_thinking",
            "room_id": room_id,
        })

        ai_response = await _generate_ai_response(
            room_id=room_id,
            user_id=user_id,
            user_message=req.content,
            thread_id=req.thread_id,
            model_override=req.model_override,
        )
        response_data["ai_response"] = ai_response

        ai_msg = {
            "type": "message",
            "message_id": ai_response["message_id"],
            "room_id": room_id,
            "author_id": "bachman",
            "author_type": "ai",
            "author_name": "Bachman",
            "content": ai_response["content"],
            "thread_id": req.thread_id,
            "model_used": ai_response["model"],
            "cost": ai_response["cost"],
            "entities_extracted": ai_response.get("entities_extracted", []),
            "created_at": created_at,
        }
        await manager.broadcast_to_room(room_id, ai_msg, exclude_user_id=user_id)

        await manager.broadcast_to_room(room_id, {
            "type": "ai_done",
            "room_id": room_id,
        })

    return response_data


async def _generate_ai_response(
    room_id: str,
    user_id: str,
    user_message: str,
    thread_id: str | None = None,
    model_override: str | None = None,
) -> dict:
    """Generate an AI response with graph context and entity extraction."""

    with get_db() as conn:
        recent = conn.execute(
            """SELECT author_type, content FROM messages
               WHERE room_id = ? ORDER BY created_at DESC LIMIT 20""",
            (room_id,)
        ).fetchall()
    history = [{"role": "assistant" if r["author_type"] == "ai" else "user", "content": r["content"]} for r in reversed(recent)]

    graph_context = get_room_context(room_id)
    decisions = get_recent_decisions(room_id)
    file_contents = get_file_contents(room_id, max_files=30)

    context_block = ""
    if graph_context:
        context_block += "\n\n--- LINKED ENTITIES (from knowledge graph) ---\n"
        seen = set()
        for item in graph_context:
            eid = item.get("entity_id") or item.get("source_id")
            if eid and eid not in seen:
                seen.add(eid)
                ename = item.get("entity_name") or item.get("source_name") or eid
                etype = item.get("entity_type", "")
                context_block += f"- [{ename}] ({etype})\n"
                if item.get("related_name"):
                    context_block += f"  → {item.get('rel_type', 'relates to')} [{item['related_name']}]\n"

    if decisions:
        context_block += "\n--- RECENT DECISIONS ---\n"
        for d in decisions[:5]:
            context_block += f"- {d.get('content', 'No content')} (by {d.get('made_by', 'unknown')})\n"

    if file_contents:
        context_block += "\n--- REPOSITORY FILES (source code) ---\n"
        for f in file_contents:
            path = f.get("path") or f.get("name", "unknown")
            branch = f.get("branch") or "main"
            content = f.get("content", "")
            if content:
                context_block += f"\n### [{branch}] {path}\n```\n{content}\n```\n"


    # Add MongoDB semantic context
    try:
        from services.mongo_store import search_all_collections
        mongo_context = search_all_collections(user_message, limit=3)
        if any(mongo_context.values()):
            context_block += "\n\n--- CUSTOMER CLINIC HISTORY (from Atlas Vector Search) ---\n"
            for collection, results_list in mongo_context.items():
                for r in results_list:
                    if r.get("feature_focus"):
                        context_block += f"- Clinic: {r['feature_focus']} — {r.get('specific_question', '')} (satisfaction: {r.get('avg_satisfaction', 'N/A')})\n"
                    elif r.get("decision"):
                        context_block += f"- Decision: {r.get('feature', '')} — {r['decision']}\n"
                    elif r.get("name"):
                        context_block += f"- Spec: {r['name']} — {r.get('description', '')}\n"
    except Exception as e:
        print(f"MongoDB context error: {e}")

    system = AI_SYSTEM_PROMPT
    if context_block:
        system += context_block

    messages = [{"role": "system", "content": system}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    # Check if custom trained model is requested
    if model_override == "custom/trained":
        from services.tinker_inference import has_trained_model, get_active_model, sample_from_trained_model
        if has_trained_model():
            active = get_active_model()
            custom_result = sample_from_trained_model(
                model_id=active["model_id"],
                user_message=user_message,
                conversation_history=history[-6:],
                graph_context=context_block,
            )
            llm_result = {
                "content": custom_result["content"],
                "model": custom_result["model"],
                "tokens_in": 0,
                "tokens_out": custom_result.get("tokens_out", 0),
                "cost": 0.0,
                "invocation_id": str(uuid.uuid4()),
            }
        else:
            llm_result = await call_llm(
                messages=messages,
                room_id=room_id,
                user_id=user_id,
                model=None,
            )
    else:
        llm_result = await call_llm(
            messages=messages,
            room_id=room_id,
            user_id=user_id,
            model=model_override,
        )

    ai_message_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            """INSERT INTO messages (message_id, room_id, author_id, author_type, content, thread_id, model_used, tokens_in, tokens_out, cost)
               VALUES (?, ?, 'assistant', 'ai', ?, ?, ?, ?, ?, ?)""",
            (ai_message_id, room_id, llm_result["content"], thread_id,
             llm_result["model"], llm_result["tokens_in"], llm_result["tokens_out"], llm_result["cost"])
        )

    audit(user_id, "ai_invoked", room_id, "message", ai_message_id, {
        "model": llm_result["model"],
        "tokens_in": llm_result["tokens_in"],
        "tokens_out": llm_result["tokens_out"],
        "cost": llm_result["cost"],
        "invocation_id": llm_result["invocation_id"],
    })

    snippet = f"User: {user_message}\n\nBachman: {llm_result['content']}"
    extraction_result = await extract_entities_from_conversation(snippet, room_id)

    return {
        "message_id": ai_message_id,
        "content": llm_result["content"],
        "model": llm_result["model"],
        "tokens_in": llm_result["tokens_in"],
        "tokens_out": llm_result["tokens_out"],
        "cost": llm_result["cost"],
        "entities_extracted": extraction_result.get("entities", []),
    }