"""
Darwin Enterprise Evolve — ADK-pattern Agent
Gemini-powered agent with MongoDB tools via OpenRouter.
"""
import os
import json
import httpx
from services.mongo_store import (
    store_clinic_session, store_design_decision, store_feature_spec,
    vector_search, search_all_collections,
)

OPENROUTER_API_KEY = None

def _get_key():
    global OPENROUTER_API_KEY
    if not OPENROUTER_API_KEY:
        OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    return OPENROUTER_API_KEY


TOOLS_SPEC = [
    {
        "type": "function",
        "function": {
            "name": "search_clinic_history",
            "description": "Search past customer clinic sessions using semantic vector search over MongoDB Atlas. Returns relevant past analyses ranked by similarity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language search query about a feature, design, or customer feedback"},
                    "limit": {"type": "integer", "description": "Max results (default 5)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_design_decisions",
            "description": "Search past design decisions using semantic vector search over MongoDB Atlas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query about design decisions"},
                    "limit": {"type": "integer", "description": "Max results"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_feature_specs",
            "description": "Search feature specifications using semantic vector search over MongoDB Atlas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query about feature specs"},
                    "limit": {"type": "integer", "description": "Max results"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "store_design_decision",
            "description": "Store a new design decision in MongoDB Atlas with vector embedding for future semantic retrieval.",
            "parameters": {
                "type": "object",
                "properties": {
                    "feature": {"type": "string", "description": "Feature name"},
                    "decision": {"type": "string", "description": "The design decision made"},
                    "rationale": {"type": "string", "description": "Why this decision was made"},
                    "evidence": {"type": "string", "description": "Customer evidence supporting the decision"},
                },
                "required": ["feature", "decision", "rationale"],
            },
        },
    },
]

TOOL_HANDLERS = {
    "search_clinic_history": lambda args: vector_search(args["query"], "clinic_sessions", args.get("limit", 5)),
    "search_design_decisions": lambda args: vector_search(args["query"], "design_decisions", args.get("limit", 5)),
    "search_feature_specs": lambda args: vector_search(args["query"], "feature_specs", args.get("limit", 5)),
    "store_design_decision": lambda args: store_design_decision({
        "feature": args["feature"], "decision": args["decision"],
        "rationale": args["rationale"], "evidence": args.get("evidence", ""),
        "author": "agent",
    }),
}

SYSTEM_INSTRUCTION = """You are a senior automotive HMI product intelligence agent for Darwin Enterprise Evolve.

Your job: help product teams make evidence-based design decisions using real customer feedback stored in MongoDB Atlas.

You have access to MongoDB Atlas Vector Search over the team's entire clinic history, design decisions, and feature specs. When a designer or PM asks about a feature:
1. Use search_clinic_history to find semantically relevant past customer feedback
2. Use search_design_decisions to find related past decisions
3. Synthesize findings into a clear recommendation with specific customer evidence
4. Use store_design_decision to record your recommendation for future queries

Always search before answering. Always cite specific customer signals. Always recommend a specific action."""


async def run_adk_agent(user_message: str, conversation_history: list = None) -> dict:
    """Run the Gemini agent with MongoDB Atlas tools via OpenRouter."""

    messages = [{"role": "system", "content": SYSTEM_INSTRUCTION}]

    if conversation_history:
        for msg in conversation_history[-6:]:
            messages.append({"role": msg.get("role", "user"), "content": msg["content"]})

    messages.append({"role": "user", "content": user_message})

    max_turns = 5
    turn = 0

    while turn < max_turns:
        turn += 1

        resp = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {_get_key()}",
                "Content-Type": "application/json",
            },
            json={
                "model": "google/gemini-2.5-flash",
                "messages": messages,
                "tools": TOOLS_SPEC,
                "max_tokens": 2000,
            },
            timeout=60.0,
        )

        if resp.status_code != 200:
            return {"content": f"Agent error: {resp.text[:200]}", "model": "gemini-2.5-flash", "turns": turn}

        data = resp.json()
        choice = data["choices"][0]
        msg = choice["message"]

        # Check for tool calls
        if msg.get("tool_calls"):
            # Add assistant message with tool calls
            messages.append(msg)

            for tc in msg["tool_calls"]:
                fn_name = tc["function"]["name"]
                fn_args = json.loads(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], str) else tc["function"]["arguments"]

                if fn_name in TOOL_HANDLERS:
                    try:
                        result = TOOL_HANDLERS[fn_name](fn_args)
                        result_str = json.dumps(result, default=str)
                    except Exception as e:
                        result_str = json.dumps({"error": str(e)})
                else:
                    result_str = json.dumps({"error": f"Unknown tool: {fn_name}"})

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result_str,
                })
        else:
            # No tool calls, we have the final response
            return {
                "content": msg.get("content", ""),
                "model": "gemini-2.5-flash (ADK agent)",
                "turns": turn,
            }

    return {
        "content": msg.get("content", "Agent reached max turns"),
        "model": "gemini-2.5-flash (ADK agent)",
        "turns": turn,
    }
