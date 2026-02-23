"""
Darwin Enterprise Evolve Beta — LLM Service
Single gateway through OpenRouter. Per-room model selection.
Every invocation logged to both SQLite and Neo4j.
"""
import os
import uuid
import httpx
from db import get_db
from services.graph import log_model_invocation

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Supported models — display name → OpenRouter model string
AVAILABLE_MODELS = {
    "claude-sonnet": "anthropic/claude-sonnet-4",
    "claude-haiku": "anthropic/claude-3.5-haiku",
    "gpt-4o": "openai/gpt-4o",
    "gpt-4o-mini": "openai/gpt-4o-mini",
    "gemini-2-flash": "google/gemini-2.0-flash-001",
    "gemini-2-pro": "google/gemini-2.0-pro-exp-02-05",
}

# Approximate costs per 1M tokens (input/output) for spend estimation
MODEL_COSTS = {
    "anthropic/claude-sonnet-4": {"input": 3.0, "output": 15.0},
    "anthropic/claude-3.5-haiku": {"input": 0.80, "output": 4.0},
    "openai/gpt-4o": {"input": 2.50, "output": 10.0},
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "google/gemini-2.0-flash-001": {"input": 0.10, "output": 0.40},
    "google/gemini-2.0-pro-exp-02-05": {"input": 1.25, "output": 5.0},
}


def get_room_default_model(room_id: str) -> str:
    """Get the default model for a room."""
    with get_db() as conn:
        row = conn.execute("SELECT default_model FROM rooms WHERE room_id = ?", (room_id,)).fetchone()
        if row:
            return row["default_model"]
    return "anthropic/claude-sonnet-4"


def estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """Estimate cost in dollars."""
    costs = MODEL_COSTS.get(model, {"input": 3.0, "output": 15.0})
    return (tokens_in * costs["input"] / 1_000_000) + (tokens_out * costs["output"] / 1_000_000)


async def call_llm(
    messages: list[dict],
    room_id: str,
    user_id: str,
    model: str | None = None,
    system_prompt: str | None = None,
    entities_cited: list[str] | None = None,
) -> dict:
    """
    Call an LLM through OpenRouter.
    Returns: {"content": str, "model": str, "tokens_in": int, "tokens_out": int, "cost": float, "invocation_id": str}
    """
    if model is None:
        model = get_room_default_model(room_id)

    # Build request
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 4096,
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://darwin-evolve.local",
        "X-Title": "Darwin Enterprise Evolve Beta",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            json=payload,
            headers=headers,
        )

        if response.status_code != 200:
            error_body = response.text
            raise Exception(f"OpenRouter error {response.status_code}: {error_body}")

        data = response.json()

    # Extract response
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    tokens_in = usage.get("prompt_tokens", 0)
    tokens_out = usage.get("completion_tokens", 0)
    cost = estimate_cost(model, tokens_in, tokens_out)
    invocation_id = str(uuid.uuid4())

    # Log to SQLite
    with get_db() as conn:
        conn.execute(
            "INSERT INTO model_invocations (invocation_id, room_id, user_id, model, tokens_in, tokens_out, cost) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (invocation_id, room_id, user_id, model, tokens_in, tokens_out, cost)
        )

    # Log to Neo4j graph
    log_model_invocation(
        invocation_id=invocation_id,
        room_id=room_id,
        user_id=user_id,
        model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost=cost,
        entities_cited=entities_cited
    )

    return {
        "content": content,
        "model": model,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost": cost,
        "invocation_id": invocation_id,
    }
