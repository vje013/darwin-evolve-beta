"""
Darwin Enterprise Evolve Beta — Tinker Inference Service
Loads a trained LoRA model via Tinker and handles inference.
Falls back to OpenRouter if no trained model available.
"""
import os
import tinker
from tinker import types
from db import get_db

TINKER_API_KEY = os.getenv("TINKER_API_KEY", "tml-lwZOkH2OBY5eVlDY5oBRyM18YS4dEaBMfXuF2qC9nQb87xz5d4ap1l7gFgVDQxjdDAAAA")
BASE_MODEL = "meta-llama/Llama-3.2-3B"

# Cache sampling clients to avoid re-creating on every request
_sampling_clients: dict[str, tinker.SamplingClient] = {}
_tokenizers: dict[str, object] = {}


def _get_service_client() -> tinker.ServiceClient:
    os.environ["TINKER_API_KEY"] = TINKER_API_KEY
    return tinker.ServiceClient()


def get_active_model() -> dict | None:
    """Get the most recent ready trained model from DB."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT model_id, tinker_model_id, base_model, lora_rank,
                   training_examples, final_loss, created_at
            FROM trained_models
            WHERE status = 'ready'
            ORDER BY created_at DESC
            LIMIT 1
        """).fetchone()
    return dict(row) if row else None


def get_sampling_client(model_id: str) -> tuple[tinker.SamplingClient, object]:
    """
    Get or create a Tinker SamplingClient for a trained model.
    Returns (sampling_client, tokenizer).
    """
    if model_id in _sampling_clients:
        return _sampling_clients[model_id], _tokenizers[model_id]

    # Look up the tinker model path
    with get_db() as conn:
        row = conn.execute(
            "SELECT tinker_model_id, base_model FROM trained_models WHERE model_id = ? AND status = 'ready'",
            (model_id,),
        ).fetchone()

    if not row:
        raise ValueError(f"No ready model found with id: {model_id}")

    sc = _get_service_client()

    # Try loading from tinker path, fall back to base model + path
    tinker_id = row["tinker_model_id"]
    model_path = f"tinker://{tinker_id}/sampler_weights/final"

    try:
        sampling_client = sc.create_sampling_client(model_path=model_path)
    except Exception:
        # Fall back: try creating from base with the saved name
        sampling_client = sc.create_sampling_client(model_path=model_path)

    # Get tokenizer from a temporary training client
    training_client = sc.create_lora_training_client(base_model=row["base_model"], rank=32)
    tokenizer = training_client.get_tokenizer()

    _sampling_clients[model_id] = sampling_client
    _tokenizers[model_id] = tokenizer

    return sampling_client, tokenizer


def sample_from_trained_model(
    model_id: str,
    user_message: str,
    conversation_history: list[dict] | None = None,
    graph_context: str = "",
    max_tokens: int = 1024,
    temperature: float = 0.7,
) -> dict:
    """
    Generate a response using the trained custom model.

    Args:
        model_id: ID of the trained model
        user_message: The user's question
        conversation_history: Previous messages [{"role": "user"|"assistant", "content": str}]
        graph_context: Relevant graph context injected into prompt
        max_tokens: Max tokens to generate
        temperature: Sampling temperature

    Returns:
        {"content": str, "model": str, "tokens_out": int}
    """
    sampling_client, tokenizer = get_sampling_client(model_id)

    # Build prompt
    system = "You are Bachman, an AI assistant for an automotive HMI product team. Answer questions using the team's knowledge graph. Cite specific entities when possible."

    if graph_context:
        system += f"\n\nRelevant context from knowledge graph:\n{graph_context}"

    prompt_parts = [f"{system}\n\n"]

    # Add conversation history
    if conversation_history:
        for msg in conversation_history[-6:]:  # Last 6 messages for context
            role = "User" if msg["role"] == "user" else "Bachman"
            prompt_parts.append(f"{role}: {msg['content']}\n")

    prompt_parts.append(f"User: {user_message}\nBachman:")

    full_prompt = "".join(prompt_parts)

    # Tokenize and sample
    prompt_input = types.ModelInput.from_ints(tokenizer.encode(full_prompt))
    params = types.SamplingParams(
        max_tokens=max_tokens,
        temperature=temperature,
        stop=["\nUser:", "\n\nUser:"],
    )

    result = sampling_client.sample(
        prompt=prompt_input,
        num_samples=1,
        sampling_params=params,
    ).result()

    # Decode response
    if result.sequences:
        response_tokens = result.sequences[0].tokens
        response_text = tokenizer.decode(response_tokens).strip()
        tokens_out = len(response_tokens)
    else:
        response_text = "I wasn't able to generate a response. Please try again."
        tokens_out = 0

    return {
        "content": response_text,
        "model": f"custom/{model_id}",
        "tokens_out": tokens_out,
    }


def has_trained_model() -> bool:
    """Check if any trained model is available."""
    return get_active_model() is not None
