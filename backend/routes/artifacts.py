"""
Darwin Enterprise Evolve Beta — Artifact Routes
Generate PRDs, extract decisions, create versioned artifacts stored in the graph.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user, check_room_access
from db import get_db
from services.llm import call_llm
from services.graph import get_driver, get_file_contents
from services.audit import audit

router = APIRouter(prefix="/rooms/{room_id}/artifacts", tags=["artifacts"])


class GenerateArtifactRequest(BaseModel):
    artifact_type: str = "PRD"  # PRD, DecisionLog, ReleaseNotes, TraceabilityMatrix, DriftDetection
    instructions: str = ""
    model_override: str | None = None

    model_config = {"protected_namespaces": ()}


ARTIFACT_PROMPTS = {
    "PRD": """Generate a Product Requirements Document (PRD) from the conversation and linked entities.
Structure it with:
1. Overview / Problem Statement
2. Requirements (functional and non-functional)
3. Design References (cite linked Figma frames, specs)
4. Technical Approach (cite linked PRs, components)
5. Open Questions / Decisions Needed
6. Traceability (which requirements link to which designs and implementations)

Use [Entity Name] citations for every artifact you reference.""",

    "DecisionLog": """Extract all decisions from this conversation.
For each decision, capture:
- Decision: What was decided
- Made by: Who made or proposed it
- Context: Why it was made
- Dependencies: What it affects
- Status: Final / Tentative / Needs Review

Format as a structured decision log.""",

    "ReleaseNotes": """Generate release notes from the conversation and linked PRs/tasks.
Structure:
- Summary of changes
- New features
- Bug fixes
- Breaking changes
- Known issues
- Contributors""",

    "TraceabilityMatrix": """Generate a traceability matrix from linked entities.
Map: Requirement → Design Spec → Implementation (PR/Task) → Test/Validation
Flag any gaps where a requirement lacks design, implementation, or testing coverage.
Present as a table with columns: Requirement | Design | Implementation | Test | Status
This is critical for ISO 26262 / ASPICE compliance.""",

    "DriftDetection": """Analyze the linked entities for drift between design and implementation.
Compare:
1. Figma designs vs code implementations — are all designed screens implemented?
2. Requirements vs PRs — are all requirements addressed by at least one PR?
3. Decisions made in chat vs what's actually built — has the team diverged from agreed plans?
4. Open issues that haven't been addressed
5. PRs that don't trace back to a requirement or decision

For each drift found, provide:
- What drifted: The specific gap
- Severity: Critical / Warning / Info
- Recommendation: What should happen next

Be specific — cite entity names and relationships.""",
}


@router.post("/generate")
async def generate_artifact(
    room_id: str,
    req: GenerateArtifactRequest,
    user: dict = Depends(get_current_user),
):
    check_room_access(user["user_id"], room_id, "member")
    user_id = user["user_id"]

    if req.artifact_type not in ARTIFACT_PROMPTS:
        raise HTTPException(400, f"Unknown artifact type. Use: {list(ARTIFACT_PROMPTS.keys())}")

    # Gather all room messages
    with get_db() as conn:
        messages = conn.execute(
            "SELECT author_type, content, created_at FROM messages WHERE room_id = ? ORDER BY created_at ASC",
            (room_id,)
        ).fetchall()

    if not messages:
        raise HTTPException(400, "No messages in this room to generate from")

    # Build conversation transcript
    transcript = "\n".join(
        f"[{m['author_type'].upper()}] {m['content']}" for m in messages
    )

    # Get linked entities from graph
    driver = get_driver()
    with driver.session() as session:
        result = session.run("""
            MATCH (r:Room {id: $room_id})-[:FOCUSES_ON]->(e:Entity)
            OPTIONAL MATCH (e)-[rel]->(related:Entity)
            RETURN e.id AS id, e.type AS type, e.name AS name,
                   collect({rel_type: type(rel), target: related.name}) AS relationships
        """, room_id=room_id)
        entities = [dict(r) for r in result]

    entity_context = ""
    if entities:
        entity_context = "\n\n--- LINKED ENTITIES ---\n"
        for e in entities:
            entity_context += f"- [{e['name']}] (type: {e['type']})\n"
            for rel in e.get("relationships", []):
                if rel.get("target"):
                    entity_context += f"  → {rel['rel_type']} [{rel['target']}]\n"

    # Add file contents for code-aware artifacts
    file_context = ""
    if req.artifact_type in ("TraceabilityMatrix", "DriftDetection", "PRD"):
        files = get_file_contents(room_id, max_files=20)
        if files:
            file_context = "\n\n--- REPOSITORY FILES (source code) ---\n"
            for f in files:
                path = f.get("path") or f.get("name", "unknown")
                branch = f.get("branch") or "main"
                content = f.get("content", "")
                if content:
                    file_context += f"\n### [{branch}] {path}\n```\n{content[:3000]}\n```\n"

    # Generate artifact
    system = ARTIFACT_PROMPTS[req.artifact_type]
    if req.instructions:
        system += f"\n\nAdditional instructions: {req.instructions}"

    llm_messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Conversation transcript:\n{transcript}{entity_context}{file_context}"}
    ]

    llm_result = await call_llm(
        messages=llm_messages,
        room_id=room_id,
        user_id=user_id,
        model=req.model_override,
    )

    # Store artifact in Neo4j as versioned node
    artifact_id = str(uuid.uuid4())
    with driver.session() as session:
        # Check for existing artifacts of this type in this room
        existing = session.run("""
            MATCH (art:Artifact {type: $type})-[:DERIVED_FROM]->(r:Room {id: $room_id})
            RETURN art.id AS id, art.version AS version
            ORDER BY art.version DESC LIMIT 1
        """, type=req.artifact_type, room_id=room_id).single()

        version = 1
        if existing:
            version = (existing["version"] or 0) + 1

        # Create artifact node
        session.run("""
            CREATE (art:Artifact {
                id: $artifact_id,
                type: $type,
                version: $version,
                content: $content,
                generated_by: $user_id,
                model_used: $model,
                created_at: datetime()
            })
            WITH art
            MATCH (r:Room {id: $room_id})
            MERGE (art)-[:DERIVED_FROM]->(r)
            WITH art
            MATCH (u:User {id: $user_id})
            MERGE (art)-[:GENERATED_BY]->(u)
        """,
            artifact_id=artifact_id,
            type=req.artifact_type,
            version=version,
            content=llm_result["content"],
            user_id=user_id,
            model=llm_result["model"],
            room_id=room_id,
        )

        # Link to referenced entities
        for entity in entities:
            session.run("""
                MATCH (art:Artifact {id: $artifact_id})
                MATCH (e:Entity {id: $entity_id})
                MERGE (art)-[:REFERENCES]->(e)
            """, artifact_id=artifact_id, entity_id=entity["id"])

        # Supersede previous version
        if existing:
            session.run("""
                MATCH (new:Artifact {id: $new_id})
                MATCH (old:Artifact {id: $old_id})
                MERGE (new)-[:SUPERSEDES]->(old)
            """, new_id=artifact_id, old_id=existing["id"])

    audit(user_id, "artifact_created", room_id, "artifact", artifact_id, {
        "type": req.artifact_type,
        "version": version,
        "model": llm_result["model"],
    })

    return {
        "artifact_id": artifact_id,
        "type": req.artifact_type,
        "version": version,
        "content": llm_result["content"],
        "model": llm_result["model"],
        "cost": llm_result["cost"],
    }


@router.get("")
async def list_artifacts(room_id: str, user: dict = Depends(get_current_user)):
    check_room_access(user["user_id"], room_id, "viewer")

    driver = get_driver()
    with driver.session() as session:
        result = session.run("""
            MATCH (art:Artifact)-[:DERIVED_FROM]->(r:Room {id: $room_id})
            OPTIONAL MATCH (art)-[:GENERATED_BY]->(u:User)
            RETURN art.id AS artifact_id, art.type AS type, art.version AS version,
                   art.created_at AS created_at, u.display_name AS generated_by
            ORDER BY art.type, art.version DESC
        """, room_id=room_id)
        return [dict(r) for r in result]


@router.get("/{artifact_id}")
async def get_artifact(room_id: str, artifact_id: str, user: dict = Depends(get_current_user)):
    check_room_access(user["user_id"], room_id, "viewer")

    driver = get_driver()
    with driver.session() as session:
        result = session.run("""
            MATCH (art:Artifact {id: $artifact_id})-[:DERIVED_FROM]->(r:Room {id: $room_id})
            OPTIONAL MATCH (art)-[:GENERATED_BY]->(u:User)
            OPTIONAL MATCH (art)-[:REFERENCES]->(e:Entity)
            RETURN art.id AS artifact_id, art.type AS type, art.version AS version,
                   art.content AS content, art.model_used AS model,
                   art.created_at AS created_at, u.display_name AS generated_by,
                   collect(e.name) AS referenced_entities
        """, artifact_id=artifact_id, room_id=room_id).single()

        if not result:
            raise HTTPException(404, "Artifact not found")

        return dict(result)
