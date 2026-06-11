"""
Darwin Enterprise Evolve Beta — Entity Extractor
After every AI response, extract entities and relationships → write to Neo4j.
Uses a cheap model (Haiku/GPT-4o-mini) for extraction to keep costs low.
The graph grows as a byproduct of conversation.
"""
import os
import json
import uuid
import httpx
from services.graph import merge_entity, create_relationship, link_entity_to_room, set_entity_attribute

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Use a cheap, fast model for extraction
EXTRACTION_MODEL = "openai/gpt-4o-mini"

EXTRACTION_SYSTEM_PROMPT = """You are an entity extraction system for an engineering team collaboration tool.
Given a conversation snippet, extract:
1. ENTITIES: Things mentioned (requirements, decisions, components, people, tools, specs, PRs, files, etc.)
2. RELATIONSHIPS: How entities relate to each other.

For each entity, provide:
- id: a snake_case unique identifier (e.g., "hvac_control_panel", "warning_banner_spec")
- type: one of [Requirement, Decision, Component, Spec, PullRequest, FigmaFrame, Task, Person, Tool, System]
- name: human-readable name
- attributes: key-value pairs of properties mentioned

For each relationship, provide:
- from_id: source entity id
- to_id: target entity id
- rel_type: relationship name in UPPER_SNAKE_CASE (e.g., IMPLEMENTS, SPECIFIED_BY, DEPENDS_ON, TRACKS, ASSIGNED_TO)
- edge_class: one of [RESOURCE, INFORMATION, AUTHORITY, CONSTRAINT, TEMPORAL]
  - RESOURCE: material/capital flow
  - INFORMATION: data/signal flow (specs, requirements, PRs, design docs)
  - AUTHORITY: decision rights, approvals, ownership
  - CONSTRAINT: blockers, dependencies, bottlenecks
  - TEMPORAL: sequencing, deadlines, scheduling

Return ONLY valid JSON with this structure:
{
  "entities": [...],
  "relationships": [...]
}

If nothing meaningful to extract, return {"entities": [], "relationships": []}.
Be selective — only extract entities that are concrete, actionable, or important for traceability.
Do NOT extract vague concepts or conversational filler."""


async def extract_entities_from_conversation(
    conversation_snippet: str,
    room_id: str,
) -> dict:
    """
    Extract entities and relationships from a conversation snippet.
    Write them to Neo4j and link to the room.
    Returns the extraction result for logging.
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://darwin-evolve.local",
        "X-Title": "Darwin Evolve Extractor",
    }

    payload = {
        "model": EXTRACTION_MODEL,
        "messages": [
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": f"Extract entities and relationships from this conversation:\n\n{conversation_snippet}"}
        ],
        "max_tokens": 2000,
        "response_format": {"type": "json_object"},
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                json=payload,
                headers=headers,
            )

            if response.status_code != 200:
                print(f"⚠ Extraction failed: {response.status_code}")
                return {"entities": [], "relationships": []}

            data = response.json()
            content = data["choices"][0]["message"]["content"]
            result = json.loads(content)

    except (json.JSONDecodeError, KeyError, Exception) as e:
        print(f"⚠ Extraction parse error: {e}")
        return {"entities": [], "relationships": []}

    # Write entities to Neo4j
    entity_ids = []
    for entity in result.get("entities", []):
        entity_id = entity.get("id", str(uuid.uuid4()))
        entity_type = entity.get("type", "Entity")
        name = entity.get("name", entity_id)

        merge_entity(entity_id, entity_type, name, source="chat_extraction")
        link_entity_to_room(entity_id, room_id)
        entity_ids.append(entity_id)

        # Write attributes via EAV
        for attr_key, attr_value in entity.get("attributes", {}).items():
            set_entity_attribute(
                entity_id=entity_id,
                attr_name=attr_key,
                value=str(attr_value),
                dtype=type(attr_value).__name__,
                source="chat_extraction"
            )

    # Write relationships to Neo4j
    for rel in result.get("relationships", []):
        try:
            create_relationship(
                from_id=rel["from_id"],
                to_id=rel["to_id"],
                rel_type=rel.get("rel_type", "RELATES_TO"),
                edge_class=rel.get("edge_class", "INFORMATION"),
                metadata={"source": "chat_extraction"}
            )
        except Exception as e:
            print(f"⚠ Relationship write failed: {e}")

    return {
        "entities": entity_ids,
        "relationships": len(result.get("relationships", [])),
    }
