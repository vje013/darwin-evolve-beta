"""
Darwin Enterprise Evolve Beta — Training Readiness & Training Job Routes
Graph density tracking, model training gate, and Tinker training pipeline.
"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from auth import get_current_user
from services.graph import get_driver
from db import get_db

router = APIRouter(prefix="/graph", tags=["training"])

TRAINING_THRESHOLDS = {
    "min_nodes": 1000,
    "min_relationships": 400,
    "min_cross_type_relationships": 100,
}


@router.get("/stats")
async def graph_stats(user: dict = Depends(get_current_user)):
    """Global graph stats: node counts by label, relationship counts, cross-type edges."""
    driver = get_driver()
    with driver.session() as session:
        node_result = session.run("""
            MATCH (e:Entity)
            RETURN e.type AS type, count(*) AS count
            ORDER BY count DESC
        """)
        node_counts = {r["type"]: r["count"] for r in node_result}

        total_nodes_result = session.run("""
            MATCH (n)
            WHERE n:Entity OR n:Artifact OR n:Decision
            RETURN count(n) AS total
        """)
        total_nodes = total_nodes_result.single()["total"]

        total_rels_result = session.run("""
            MATCH (a:Entity)-[r]->(b:Entity)
            RETURN count(r) AS total
        """)
        total_relationships = total_rels_result.single()["total"]

        cross_type_result = session.run("""
            MATCH (a:Entity)-[r]->(b:Entity)
            WHERE a.type <> b.type
            RETURN count(r) AS total
        """)
        cross_type_relationships = cross_type_result.single()["total"]

        rel_types_result = session.run("""
            MATCH (a:Entity)-[r]->(b:Entity)
            RETURN type(r) AS rel_type, count(*) AS count
            ORDER BY count DESC
        """)
        rel_type_counts = {r["rel_type"]: r["count"] for r in rel_types_result}

    return {
        "total_nodes": total_nodes,
        "total_relationships": total_relationships,
        "cross_type_relationships": cross_type_relationships,
        "node_counts_by_type": node_counts,
        "relationship_type_counts": rel_type_counts,
    }


@router.get("/training-readiness")
async def training_readiness(user: dict = Depends(get_current_user)):
    """Check if graph is dense enough for custom model training."""
    driver = get_driver()
    with driver.session() as session:
        total_nodes_result = session.run("""
            MATCH (n)
            WHERE n:Entity OR n:Artifact OR n:Decision
            RETURN count(n) AS total
        """)
        total_nodes = total_nodes_result.single()["total"]

        total_rels_result = session.run("""
            MATCH (a:Entity)-[r]->(b:Entity)
            RETURN count(r) AS total
        """)
        total_relationships = total_rels_result.single()["total"]

        cross_type_result = session.run("""
            MATCH (a:Entity)-[r]->(b:Entity)
            WHERE a.type <> b.type
            RETURN count(r) AS total
        """)
        cross_type_relationships = cross_type_result.single()["total"]

        node_result = session.run("""
            MATCH (e:Entity)
            RETURN e.type AS type, count(*) AS count
            ORDER BY count DESC
        """)
        node_counts = {r["type"]: r["count"] for r in node_result}

    ready = (
        total_relationships >= TRAINING_THRESHOLDS["min_relationships"]
        and cross_type_relationships >= TRAINING_THRESHOLDS["min_cross_type_relationships"]
    )

    deficit = max(0, TRAINING_THRESHOLDS["min_relationships"] - total_relationships)
    estimated_weeks = round(deficit / 70) if deficit > 0 else 0

    # Check if a model is already trained
    with get_db() as conn:
        existing_model = conn.execute(
            "SELECT model_id, created_at, final_loss, training_examples FROM trained_models WHERE status='ready' ORDER BY created_at DESC LIMIT 1"
        ).fetchone()

    # Check if training is in progress
    with get_db() as conn:
        active_job = conn.execute(
            "SELECT job_id, status, progress, message FROM training_jobs WHERE status NOT IN ('complete', 'error') ORDER BY created_at DESC LIMIT 1"
        ).fetchone()

    return {
        "ready": ready,
        "thresholds": TRAINING_THRESHOLDS,
        "current": {
            "total_nodes": total_nodes,
            "total_relationships": total_relationships,
            "cross_type_relationships": cross_type_relationships,
            "node_counts_by_type": node_counts,
        },
        "progress": {
            "relationships_pct": min(100, round(total_relationships / TRAINING_THRESHOLDS["min_relationships"] * 100)),
            "cross_type_pct": min(100, round(cross_type_relationships / TRAINING_THRESHOLDS["min_cross_type_relationships"] * 100)),
        },
        "estimated_weeks_to_ready": estimated_weeks,
        "existing_model": dict(existing_model) if existing_model else None,
        "active_job": dict(active_job) if active_job else None,
    }


# --- Training Jobs ---

@router.post("/train")
async def start_training(
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    """Kick off a Tinker LoRA training job. Runs in background."""
    # Check readiness
    driver = get_driver()
    with driver.session() as session:
        total_rels_result = session.run("MATCH (a:Entity)-[r]->(b:Entity) RETURN count(r) AS total")
        total_relationships = total_rels_result.single()["total"]

        cross_type_result = session.run("MATCH (a:Entity)-[r]->(b:Entity) WHERE a.type <> b.type RETURN count(r) AS total")
        cross_type_relationships = cross_type_result.single()["total"]

    if total_relationships < TRAINING_THRESHOLDS["min_relationships"]:
        raise HTTPException(400, f"Graph not ready: {total_relationships}/{TRAINING_THRESHOLDS['min_relationships']} relationships")
    if cross_type_relationships < TRAINING_THRESHOLDS["min_cross_type_relationships"]:
        raise HTTPException(400, f"Graph not ready: {cross_type_relationships}/{TRAINING_THRESHOLDS['min_cross_type_relationships']} cross-type relationships")

    # Check for active training jobs
    with get_db() as conn:
        active = conn.execute(
            "SELECT job_id FROM training_jobs WHERE status NOT IN ('complete', 'error') LIMIT 1"
        ).fetchone()
    if active:
        raise HTTPException(409, f"Training already in progress: {active['job_id']}")

    # Create job
    job_id = str(uuid.uuid4())[:12]
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO training_jobs (job_id, status, progress, message, created_at, updated_at, created_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (job_id, "queued", 0, "Training job queued", now, now, user["user_id"]),
        )

    # Run training in background
    from services.tinker_trainer import run_training
    background_tasks.add_task(run_training, job_id)

    return {"job_id": job_id, "status": "queued"}


@router.get("/train/{job_id}")
async def get_training_status(job_id: str, user: dict = Depends(get_current_user)):
    """Poll training job status."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM training_jobs WHERE job_id = ?", (job_id,)
        ).fetchone()

    if not row:
        raise HTTPException(404, "Training job not found")

    return dict(row)


@router.get("/models")
async def list_trained_models(user: dict = Depends(get_current_user)):
    """List all trained models."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM trained_models ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]
