"""
Darwin Enterprise Evolve Beta — Graph Service
Neo4j EAV graph with five-edge-type schema for Enterprise Evolve compatibility.

Edge Types (from Enterprise Evolve spec):
  RESOURCE    — material/capital flow
  INFORMATION — data/signal flow
  AUTHORITY   — decision rights, approvals
  CONSTRAINT  — bottlenecks, dependencies, blockers
  TEMPORAL    — sequencing, scheduling, deadlines

Entity-Attribute-Value pattern:
  (Entity)-[:HAS_ATTR]->(Attribute)-[:HAS_VALUE]->(Value {value, dtype, source, valid_from, valid_to})
"""
import os
from datetime import datetime, timezone
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7688")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "darwin2026")

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return _driver


def close_driver():
    global _driver
    if _driver:
        _driver.close()
        _driver = None


def init_graph():
    """Bootstrap Neo4j schema: constraints, indexes, and edge type registry."""
    driver = get_driver()
    with driver.session() as session:
        # Uniqueness constraints
        constraints = [
            "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
            "CREATE CONSTRAINT room_id IF NOT EXISTS FOR (r:Room) REQUIRE r.id IS UNIQUE",
            "CREATE CONSTRAINT audit_id IF NOT EXISTS FOR (a:AuditEvent) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT artifact_id IF NOT EXISTS FOR (art:Artifact) REQUIRE art.id IS UNIQUE",
            "CREATE CONSTRAINT decision_id IF NOT EXISTS FOR (d:Decision) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT invocation_id IF NOT EXISTS FOR (i:ModelInvocation) REQUIRE i.id IS UNIQUE",
        ]
        for c in constraints:
            try:
                session.run(c)
            except Exception:
                pass  # Constraint may already exist

        # Register the five edge types as metadata nodes
        session.run("""
            UNWIND ['RESOURCE', 'INFORMATION', 'AUTHORITY', 'CONSTRAINT', 'TEMPORAL'] AS etype
            MERGE (e:EdgeType {name: etype})
            SET e.description = CASE etype
                WHEN 'RESOURCE' THEN 'Material and capital flow'
                WHEN 'INFORMATION' THEN 'Data and signal flow'
                WHEN 'AUTHORITY' THEN 'Decision rights and approvals'
                WHEN 'CONSTRAINT' THEN 'Bottlenecks and dependencies'
                WHEN 'TEMPORAL' THEN 'Sequencing and scheduling'
            END
        """)

    print("✅ Neo4j graph initialized with five-edge-type schema")


# --- Core Graph Operations ---

def create_user_node(user_id: str, email: str, display_name: str):
    driver = get_driver()
    with driver.session() as session:
        session.run("""
            MERGE (u:User {id: $user_id})
            SET u.email = $email,
                u.display_name = $display_name,
                u.created_at = datetime()
        """, user_id=user_id, email=email, display_name=display_name)


def create_room_node(room_id: str, name: str, created_by: str):
    driver = get_driver()
    with driver.session() as session:
        session.run("""
            MERGE (r:Room {id: $room_id})
            SET r.name = $name, r.created_at = datetime()
            WITH r
            MATCH (u:User {id: $created_by})
            MERGE (u)-[:CREATED]->(r)
        """, room_id=room_id, name=name, created_by=created_by)


def write_audit_event(
    audit_id: str,
    user_id: str,
    room_id: str | None,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    metadata: dict | None = None
):
    """Write an audit event as a graph node with edges to actor and room."""
    driver = get_driver()
    with driver.session() as session:
        # Create audit node
        session.run("""
            CREATE (a:AuditEvent {
                id: $audit_id,
                action: $action,
                target_type: $target_type,
                target_id: $target_id,
                metadata: $metadata_str,
                timestamp: datetime()
            })
            WITH a
            MATCH (u:User {id: $user_id})
            MERGE (a)-[:BY]->(u)
        """,
            audit_id=audit_id,
            action=action,
            target_type=target_type or "",
            target_id=target_id or "",
            metadata_str=str(metadata or {}),
            user_id=user_id
        )

        # Link to room if applicable
        if room_id:
            session.run("""
                MATCH (a:AuditEvent {id: $audit_id})
                MATCH (r:Room {id: $room_id})
                MERGE (a)-[:IN]->(r)
            """, audit_id=audit_id, room_id=room_id)


def log_model_invocation(
    invocation_id: str,
    room_id: str,
    user_id: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
    cost: float,
    entities_cited: list[str] | None = None
):
    """Log an LLM invocation as a graph node for spend tracking and audit."""
    driver = get_driver()
    with driver.session() as session:
        session.run("""
            CREATE (i:ModelInvocation {
                id: $invocation_id,
                model: $model,
                tokens_in: $tokens_in,
                tokens_out: $tokens_out,
                cost: $cost,
                timestamp: datetime()
            })
            WITH i
            MATCH (r:Room {id: $room_id})
            MERGE (i)-[:IN_ROOM]->(r)
            WITH i
            MATCH (u:User {id: $user_id})
            MERGE (i)-[:TRIGGERED_BY]->(u)
        """,
            invocation_id=invocation_id,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost=cost,
            room_id=room_id,
            user_id=user_id
        )

        # Link to cited entities
        if entities_cited:
            for entity_id in entities_cited:
                session.run("""
                    MATCH (i:ModelInvocation {id: $invocation_id})
                    MATCH (e:Entity {id: $entity_id})
                    MERGE (i)-[:CITED]->(e)
                """, invocation_id=invocation_id, entity_id=entity_id)


def merge_entity(entity_id: str, entity_type: str, name: str, source: str = "chat"):
    """Create or update an entity node."""
    driver = get_driver()
    with driver.session() as session:
        session.run("""
            MERGE (e:Entity {id: $entity_id})
            SET e.type = $entity_type,
                e.name = $name,
                e.source = $source,
                e.updated_at = datetime()
        """, entity_id=entity_id, entity_type=entity_type, name=name, source=source)


def set_entity_attribute(entity_id: str, attr_name: str, value: str, dtype: str = "string", source: str = "chat"):
    """EAV pattern: (Entity)-[:HAS_ATTR]->(Attribute)-[:HAS_VALUE]->(Value)"""
    driver = get_driver()
    now = datetime.now(timezone.utc).isoformat()
    with driver.session() as session:
        session.run("""
            MATCH (e:Entity {id: $entity_id})
            MERGE (a:Attribute {name: $attr_name})
            MERGE (e)-[:HAS_ATTR]->(a)
            CREATE (v:Value {
                value: $value,
                dtype: $dtype,
                source: $source,
                valid_from: $valid_from,
                valid_to: null
            })
            MERGE (a)-[:HAS_VALUE]->(v)
        """,
            entity_id=entity_id,
            attr_name=attr_name,
            value=value,
            dtype=dtype,
            source=source,
            valid_from=now
        )


def create_relationship(from_id: str, to_id: str, rel_type: str, edge_class: str, metadata: dict | None = None):
    """
    Create a typed relationship between two entities.
    edge_class must be one of: RESOURCE, INFORMATION, AUTHORITY, CONSTRAINT, TEMPORAL
    """
    valid_classes = {"RESOURCE", "INFORMATION", "AUTHORITY", "CONSTRAINT", "TEMPORAL"}
    if edge_class not in valid_classes:
        raise ValueError(f"edge_class must be one of {valid_classes}")

    driver = get_driver()
    with driver.session() as session:
        # Neo4j doesn't allow parameterized relationship types, so we use APOC or a generic rel
        session.run(f"""
            MATCH (a:Entity {{id: $from_id}})
            MATCH (b:Entity {{id: $to_id}})
            MERGE (a)-[r:{rel_type} {{edge_class: $edge_class}}]->(b)
            SET r.created_at = datetime(),
                r.metadata = $metadata_str
        """,
            from_id=from_id,
            to_id=to_id,
            edge_class=edge_class,
            metadata_str=str(metadata or {})
        )


def link_entity_to_room(entity_id: str, room_id: str):
    """Link an entity to a room so it appears in context queries."""
    driver = get_driver()
    with driver.session() as session:
        session.run("""
            MATCH (e:Entity {id: $entity_id})
            MATCH (r:Room {id: $room_id})
            MERGE (r)-[:FOCUSES_ON]->(e)
        """, entity_id=entity_id, room_id=room_id)


def get_room_context(room_id: str, entity_ids: list[str] | None = None, max_hops: int = 2) -> list[dict]:
    """
    Get context for AI: room-linked entities + 2-hop neighborhood of referenced entities.
    Returns a list of dicts describing entities and their relationships.
    """
    driver = get_driver()
    with driver.session() as session:
        # Get room-linked entities
        result = session.run("""
            MATCH (r:Room {id: $room_id})-[:FOCUSES_ON]->(e:Entity)
            OPTIONAL MATCH (e)-[rel]->(related:Entity)
            RETURN e.id AS entity_id, e.type AS entity_type, e.name AS entity_name,
                   type(rel) AS rel_type, related.id AS related_id, related.name AS related_name
            LIMIT 100
        """, room_id=room_id)

        context = []
        for record in result:
            context.append(dict(record))

        # If specific entities referenced, get their 2-hop neighborhood
        if entity_ids:
            result = session.run("""
                UNWIND $entity_ids AS eid
                MATCH (e:Entity {id: eid})
                OPTIONAL MATCH path = (e)-[*1..2]-(neighbor:Entity)
                WITH e, neighbor, relationships(path) AS rels
                RETURN e.id AS source_id, e.name AS source_name,
                       neighbor.id AS neighbor_id, neighbor.name AS neighbor_name,
                       [r IN rels | type(r)] AS rel_chain
                LIMIT 200
            """, entity_ids=entity_ids)

            for record in result:
                context.append(dict(record))

        return context


def get_recent_decisions(room_id: str, limit: int = 10) -> list[dict]:
    """Get recent decisions made in a room."""
    driver = get_driver()
    with driver.session() as session:
        result = session.run("""
            MATCH (d:Decision)-[:MADE_IN]->(r:Room {id: $room_id})
            RETURN d.id AS decision_id, d.content AS content,
                   d.made_by AS made_by, d.timestamp AS timestamp
            ORDER BY d.timestamp DESC
            LIMIT $limit
        """, room_id=room_id, limit=limit)
        return [dict(r) for r in result]


def get_file_contents(room_id: str, max_files: int = 10) -> list[dict]:
    """
    Get file contents from the graph for code-aware AI responses.
    Returns files linked to the room that have content stored.
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.run("""
            MATCH (r:Room {id: $room_id})-[:FOCUSES_ON]->(f:Entity {type: 'File'})
            OPTIONAL MATCH (f)-[:HAS_ATTR]->(a:Attribute {name: 'content'})-[:HAS_VALUE]->(v:Value)
            OPTIONAL MATCH (f)-[:HAS_ATTR]->(pa:Attribute {name: 'path'})-[:HAS_VALUE]->(pv:Value)
            OPTIONAL MATCH (f)-[:HAS_ATTR]->(ba:Attribute {name: 'branch'})-[:HAS_VALUE]->(bv:Value)
            WHERE v IS NOT NULL
            RETURN f.id AS file_id, f.name AS name,
                   pv.value AS path, bv.value AS branch, v.value AS content
            LIMIT $max_files
        """, room_id=room_id, max_files=max_files)
        return [dict(r) for r in result]


def get_entity_attributes(entity_id: str) -> dict:
    """Get all current attributes for an entity as a flat dict."""
    driver = get_driver()
    with driver.session() as session:
        result = session.run("""
            MATCH (e:Entity {id: $entity_id})-[:HAS_ATTR]->(a:Attribute)-[:HAS_VALUE]->(v:Value)
            WHERE v.valid_to IS NULL OR v.valid_to > datetime()
            RETURN a.name AS attr_name, v.value AS attr_value, v.dtype AS dtype
        """, entity_id=entity_id)
        attrs = {}
        for record in result:
            attrs[record["attr_name"]] = record["attr_value"]
        return attrs
