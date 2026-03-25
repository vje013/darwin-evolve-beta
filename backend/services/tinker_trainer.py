"""
Darwin Enterprise Evolve Beta — Tinker Training Service
LoRA fine-tuning on Llama 3.2-3B via Tinker API.
Generates training data from Neo4j graph, trains, saves weights.
"""
import os
import json
import numpy as np
from datetime import datetime, timezone

import tinker
from tinker import types

from services.training_data import generate_training_data
from db import get_db

# Tinker config
TINKER_API_KEY = os.getenv("TINKER_API_KEY", "tml-lwZOkH2OBY5eVlDY5oBRyM18YS4dEaBMfXuF2qC9nQb87xz5d4ap1l7gFgVDQxjdDAAAA")
BASE_MODEL = "meta-llama/Llama-3.2-3B"
LORA_RANK = 32
LEARNING_RATE = 1e-4
BATCH_SIZE = 8  # examples per forward_backward call
NUM_EPOCHS = 3


def _get_service_client() -> tinker.ServiceClient:
    """Create Tinker ServiceClient."""
    os.environ["TINKER_API_KEY"] = TINKER_API_KEY
    return tinker.ServiceClient()


def _process_example(example: dict, tokenizer) -> types.Datum:
    """Convert a prompt/completion pair into a Tinker Datum for training."""
    prompt = f"You are an AI assistant for an automotive HMI product team. Answer based on the team's knowledge graph.\n\nQuestion: {example['prompt']}\nAnswer:"
    completion = f" {example['completion']}\n\n"

    prompt_tokens = tokenizer.encode(prompt, add_special_tokens=True)
    prompt_weights = [0] * len(prompt_tokens)

    completion_tokens = tokenizer.encode(completion, add_special_tokens=False)
    completion_weights = [1] * len(completion_tokens)

    tokens = prompt_tokens + completion_tokens
    weights = prompt_weights + completion_weights

    input_tokens = tokens[:-1]
    target_tokens = tokens[1:]
    weights = weights[1:]

    return types.Datum(
        model_input=types.ModelInput.from_ints(tokens=input_tokens),
        loss_fn_inputs=dict(weights=weights, target_tokens=target_tokens),
    )


def run_training(job_id: str, on_progress=None):
    """
    Full training pipeline:
    1. Generate training data from Neo4j graph
    2. Create Tinker LoRA training client on Llama 3.2-3B
    3. Train for N epochs
    4. Save weights and create sampling client
    5. Store model manifest in SQLite

    Args:
        job_id: Training job ID for status tracking
        on_progress: Optional callback(status, progress_pct, message)
    """
    def update(status, pct, msg):
        """Update job status in DB and call callback."""
        now = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            conn.execute(
                "UPDATE training_jobs SET status=?, progress=?, message=?, updated_at=? WHERE job_id=?",
                (status, pct, msg, now, job_id),
            )
        if on_progress:
            on_progress(status, pct, msg)
        print(f"[Training {job_id}] {status} ({pct}%): {msg}")

    try:
        # Step 1: Generate training data
        update("generating_data", 5, "Querying knowledge graph...")
        examples = generate_training_data()
        num_examples = len(examples)

        if num_examples < 10:
            update("error", 0, f"Not enough training data: {num_examples} examples. Need at least 10.")
            return

        update("generating_data", 15, f"Generated {num_examples} training examples from graph")

        # Step 2: Create Tinker training client
        update("initializing", 20, f"Creating LoRA training client (rank={LORA_RANK}) on {BASE_MODEL}...")
        sc = _get_service_client()
        training_client = sc.create_lora_training_client(
            base_model=BASE_MODEL,
            rank=LORA_RANK,
        )
        tokenizer = training_client.get_tokenizer()

        update("initializing", 25, "Tokenizing training data...")

        # Process all examples into Tinker Datums
        processed = []
        for ex in examples:
            try:
                datum = _process_example(ex, tokenizer)
                processed.append(datum)
            except Exception as e:
                continue  # Skip malformed examples

        if len(processed) < 10:
            update("error", 0, f"Only {len(processed)} examples survived tokenization. Need at least 10.")
            return

        update("initializing", 30, f"Tokenized {len(processed)} examples. Starting training...")

        # Step 3: Train
        total_steps = NUM_EPOCHS * (len(processed) // BATCH_SIZE + 1)
        step = 0
        losses = []

        for epoch in range(NUM_EPOCHS):
            # Shuffle each epoch
            import random
            random.shuffle(processed)

            for batch_start in range(0, len(processed), BATCH_SIZE):
                batch = processed[batch_start:batch_start + BATCH_SIZE]
                if not batch:
                    continue

                # Forward + backward
                fwdbwd_future = training_client.forward_backward(batch, "cross_entropy")
                optim_future = training_client.optim_step(types.AdamParams(learning_rate=LEARNING_RATE))

                fwdbwd_result = fwdbwd_future.result()
                optim_result = optim_future.result()

                # Compute loss
                logprobs = np.concatenate([
                    output['logprobs'].tolist()
                    for output in fwdbwd_result.loss_fn_outputs
                ])
                weights = np.concatenate([
                    ex.loss_fn_inputs['weights'].tolist()
                    for ex in batch
                ])
                loss = -np.dot(logprobs, weights) / max(weights.sum(), 1)
                losses.append(float(loss))

                step += 1
                pct = 30 + int((step / total_steps) * 55)  # 30-85% range
                update("training", min(pct, 85),
                       f"Epoch {epoch+1}/{NUM_EPOCHS}, Step {step}/{total_steps}, Loss: {loss:.4f}")

        avg_final_loss = np.mean(losses[-10:]) if losses else 0.0
        update("saving", 88, f"Training complete. Final loss: {avg_final_loss:.4f}. Saving weights...")

        # Step 4: Save weights and create sampling client
        sampling_client = training_client.save_weights_and_get_sampling_client(
            name=f"darwin-evolve-{job_id}"
        )

        # Get model info for manifest
        info = training_client.get_info()
        model_id = info.model_data.model_id if hasattr(info, 'model_data') else job_id

        update("saving", 92, "Saving model manifest...")

        # Step 5: Store in SQLite
        now = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            conn.execute("""
                INSERT INTO trained_models
                (model_id, tinker_model_id, base_model, lora_rank, training_examples,
                 final_loss, status, created_at, job_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"darwin-evolve-{job_id}",
                str(model_id),
                BASE_MODEL,
                LORA_RANK,
                len(processed),
                float(avg_final_loss),
                "ready",
                now,
                job_id,
            ))

            # Update job as complete
            conn.execute(
                """UPDATE training_jobs
                   SET status='complete', progress=100, message=?,
                       model_id=?, completed_at=?
                   WHERE job_id=?""",
                (f"Model trained on {len(processed)} examples. Loss: {avg_final_loss:.4f}",
                 f"darwin-evolve-{job_id}", now, job_id),
            )

        print(f"[Training {job_id}] ✅ Complete. Model: darwin-evolve-{job_id}")

    except Exception as e:
        update("error", 0, f"Training failed: {str(e)}")
        raise
