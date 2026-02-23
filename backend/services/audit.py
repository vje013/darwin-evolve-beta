"""
Darwin Enterprise Evolve Beta — Audit Service
Every state-changing action gets an audit node in Neo4j.
The audit trail IS the graph.
"""
import uuid
from services.graph import write_audit_event


def audit(
    user_id: str,
    action: str,
    room_id: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    metadata: dict | None = None,
):
    """Write an audit event. Call this from every endpoint that changes state."""
    write_audit_event(
        audit_id=str(uuid.uuid4()),
        user_id=user_id,
        room_id=room_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        metadata=metadata,
    )
