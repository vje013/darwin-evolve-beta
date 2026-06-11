"""
Darwin Enterprise Evolve Beta — Connector Routes
GitHub and Figma integrations with sync, plus manual entity linking.
"""
import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user, check_room_access
from db import get_db
from services.trello_connector import sync_trello_board
from services.graph import merge_entity, link_entity_to_room, create_relationship, get_driver
from services.audit import audit
from services.github_connector import sync_github_repo
from services.figma_connector import sync_figma_file

router = APIRouter(prefix="/rooms/{room_id}/connectors", tags=["connectors"])


class LinkConnectorRequest(BaseModel):
    connector_type: str  # "github" or "figma"
    config: dict


class SyncConnectorRequest(BaseModel):
    connector_id: str


class LinkEntityRequest(BaseModel):
    entity_type: str
    entity_id: str
    name: str
    url: str = ""
    attributes: dict = {}
    edge_class: str = "INFORMATION"


# --- Connector Management ---

@router.post("")
async def link_connector(room_id: str, req: LinkConnectorRequest, user: dict = Depends(get_current_user)):
    check_room_access(user["user_id"], room_id, "admin")

    if req.connector_type not in ("github", "figma", "trello"):
        raise HTTPException(400, "Connector type must be: github, figma, or trello")

    # Validate config
    if req.connector_type == "github":
        if "repo" not in req.config or "token" not in req.config:
            raise HTTPException(400, "GitHub connector requires 'repo' (owner/repo) and 'token' fields")
    elif req.connector_type == "figma":
        if "file_key" not in req.config or "token" not in req.config:
            raise HTTPException(400, "Figma connector requires 'file_key' and 'token' fields")
    elif req.connector_type == "trello":
        if "board_id" not in req.config or "token" not in req.config:
            raise HTTPException(400, "Trello connector requires 'board_id' and 'token' fields")
        if "api_key" not in req.config:
            req.config["api_key"] = "0c72fa43801765331b7a5c9818336ec7"

    connector_id = str(uuid.uuid4())

    with get_db() as conn:
        conn.execute(
            "INSERT INTO connectors (connector_id, room_id, connector_type, config, created_by) VALUES (?, ?, ?, ?, ?)",
            (connector_id, room_id, req.connector_type, json.dumps(req.config), user["user_id"])
        )

    audit(user["user_id"], "connector_linked", room_id, "connector", connector_id, {
        "type": req.connector_type,
    })

    # Auto-sync on connect
    sync_result = await _sync_connector(connector_id, room_id, req.connector_type, req.config, user["user_id"])

    return {
        "connector_id": connector_id,
        "type": req.connector_type,
        "sync_result": sync_result,
    }


@router.get("")
async def list_connectors(room_id: str, user: dict = Depends(get_current_user)):
    check_room_access(user["user_id"], room_id, "viewer")

    with get_db() as conn:
        rows = conn.execute(
            """SELECT connector_id, connector_type, last_synced_at, created_at
               FROM connectors WHERE room_id = ?""",
            (room_id,)
        ).fetchall()

    return [dict(r) for r in rows]


@router.post("/sync/{connector_id}")
async def sync_connector(room_id: str, connector_id: str, user: dict = Depends(get_current_user)):
    """Manually trigger a sync for a connector."""
    check_room_access(user["user_id"], room_id, "member")

    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM connectors WHERE connector_id = ? AND room_id = ?",
            (connector_id, room_id)
        ).fetchone()

    if not row:
        raise HTTPException(404, "Connector not found")

    config = json.loads(row["config"])
    result = await _sync_connector(connector_id, room_id, row["connector_type"], config, user["user_id"])

    return {"connector_id": connector_id, "sync_result": result}


@router.post("/sync-all")
async def sync_all_connectors(room_id: str, user: dict = Depends(get_current_user)):
    """Sync all connectors for a room."""
    check_room_access(user["user_id"], room_id, "member")

    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM connectors WHERE room_id = ?", (room_id,)
        ).fetchall()

    results = []
    for row in rows:
        config = json.loads(row["config"])
        result = await _sync_connector(row["connector_id"], room_id, row["connector_type"], config, user["user_id"])
        results.append({"connector_id": row["connector_id"], "type": row["connector_type"], "result": result})

    return results


async def _sync_connector(connector_id: str, room_id: str, connector_type: str, config: dict, user_id: str) -> dict:
    """Internal: dispatch sync to the right connector service."""
    try:
        if connector_type == "github":
            result = await sync_github_repo(
                room_id=room_id,
                repo=config["repo"],
                token=config["token"],
                user_id=user_id,
                since=config.get("since"),
            )
        elif connector_type == "figma":
            result = await sync_figma_file(
                room_id=room_id,
                file_key=config["file_key"],
                token=config["token"],
                user_id=user_id,
            )
        elif connector_type == "trello":
            result = await sync_trello_board(
                room_id=room_id,
                board_id=config["board_id"],
                api_key=config.get("api_key", "0c72fa43801765331b7a5c9818336ec7"),
                token=config["token"],
                user_id=user_id,
    )
        else:
            return {"error": f"Unknown connector type: {connector_type}"}

        # Update last_synced_at
        now = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            conn.execute(
                "UPDATE connectors SET last_synced_at = ? WHERE connector_id = ?",
                (now, connector_id)
            )

        return result
    except Exception as e:
        return {"error": str(e)}


# --- Linked Entities (graph query) ---

@router.get("/entities")
async def list_linked_entities(room_id: str, user: dict = Depends(get_current_user)):
    """Get all entities linked to this room from the graph."""
    check_room_access(user["user_id"], room_id, "viewer")

    driver = get_driver()
    with driver.session() as session:
        result = session.run("""
            MATCH (r:Room {id: $room_id})-[:FOCUSES_ON]->(e:Entity)
            OPTIONAL MATCH (e)-[rel]->(related:Entity)
            RETURN e.id AS id, e.type AS type, e.name AS name, e.source AS source,
                   e.updated_at AS updated_at,
                   collect(DISTINCT {rel_type: type(rel), target_id: related.id, target_name: related.name}) AS relationships
            ORDER BY e.updated_at DESC
        """, room_id=room_id)

        entities = []
        for record in result:
            entity = dict(record)
            # Filter out empty relationships
            entity["relationships"] = [r for r in entity.get("relationships", []) if r.get("target_name")]
            entities.append(entity)

    return entities


@router.get("/graph")
async def get_graph_data(room_id: str, user: dict = Depends(get_current_user)):
    """Get graph data formatted for D3 force-directed visualization (nodes + links)."""
    check_room_access(user["user_id"], room_id, "viewer")

    driver = get_driver()
    with driver.session() as session:
        nodes_result = session.run("""
            MATCH (r:Room {id: $room_id})-[:FOCUSES_ON]->(e:Entity)
            RETURN e.id AS id, e.type AS type, e.name AS name, e.source AS source
        """, room_id=room_id)

        nodes = []
        node_ids = set()
        for record in nodes_result:
            node = dict(record)
            nodes.append(node)
            node_ids.add(node["id"])

        links_result = session.run("""
            MATCH (r:Room {id: $room_id})-[:FOCUSES_ON]->(e:Entity)
            MATCH (e)-[rel]->(target:Entity)
            WHERE (r)-[:FOCUSES_ON]->(target)
            RETURN e.id AS source, target.id AS target, type(rel) AS rel_type
        """, room_id=room_id)

        links = []
        for record in links_result:
            link = dict(record)
            if link["source"] in node_ids and link["target"] in node_ids:
                links.append(link)

        artifacts_result = session.run("""
            MATCH (art:Artifact)-[:DERIVED_FROM]->(r:Room {id: $room_id})
            OPTIONAL MATCH (art)-[:REFERENCES]->(e:Entity)
            RETURN art.id AS id, art.type AS type, 'Artifact' AS source,
                   art.type + ' v' + toString(art.version) AS name,
                   collect(e.id) AS references
        """, room_id=room_id)

        for record in artifacts_result:
            art = dict(record)
            art_id = art["id"]
            nodes.append({"id": art_id, "type": art["type"], "name": art["name"], "source": "artifact"})
            node_ids.add(art_id)
            for ref_id in art.get("references", []):
                if ref_id in node_ids:
                    links.append({"source": art_id, "target": ref_id, "rel_type": "REFERENCES"})

    return {"nodes": nodes, "links": links}


# --- Manual Entity Linking ---

@router.post("/entities")
async def link_entity_to_room_manually(room_id: str, req: LinkEntityRequest, user: dict = Depends(get_current_user)):
    check_room_access(user["user_id"], room_id, "member")

    merge_entity(req.entity_id, req.entity_type, req.name, source=req.entity_type.lower())

    from services.graph import set_entity_attribute
    if req.url:
        set_entity_attribute(req.entity_id, "url", req.url, "string", req.entity_type.lower())
    for key, value in req.attributes.items():
        set_entity_attribute(req.entity_id, key, str(value), type(value).__name__, req.entity_type.lower())

    link_entity_to_room(req.entity_id, room_id)

    audit(user["user_id"], "entity_linked", room_id, req.entity_type, req.entity_id, {
        "name": req.name,
        "edge_class": req.edge_class,
    })

    return {"entity_id": req.entity_id, "type": req.entity_type, "name": req.name, "linked_to_room": room_id}


@router.delete("/connectors/{connector_id}")
async def remove_connector(room_id: str, connector_id: str, user: dict = Depends(get_current_user)):
    check_room_access(user["user_id"], room_id, "admin")

    with get_db() as conn:
        result = conn.execute(
            "DELETE FROM connectors WHERE connector_id = ? AND room_id = ?",
            (connector_id, room_id)
        )
        if result.rowcount == 0:
            raise HTTPException(404, "Connector not found")

    audit(user["user_id"], "connector_removed", room_id, "connector", connector_id)

    return {"removed": connector_id}
