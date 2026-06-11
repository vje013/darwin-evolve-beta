"""
Darwin Enterprise Evolve — MongoDB Atlas Store
Vector search over customer clinic history, design decisions, feature specs.
Voyage AI embeddings auto-generated on write.
"""
import os
from datetime import datetime, timezone
from pymongo import MongoClient
import voyageai

MONGO_URI = os.getenv("MONGO_URI", "")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY", "")

_client = None
_voyage = None


def _get_db():
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI)
    return _client["darwin_evolve"]


def _get_voyage():
    global _voyage
    if _voyage is None:
        _voyage = voyageai.Client(api_key=VOYAGE_API_KEY)
    return _voyage


def _embed(text: str) -> list[float]:
    """Generate embedding via Voyage AI."""
    result = _get_voyage().embed([text], model="voyage-3-lite")
    return result.embeddings[0]


# --- Write Operations ---

def store_clinic_session(session_data: dict) -> str:
    """Store a customer clinic analysis result with auto-embedding."""
    db = _get_db()
    doc = {
        "feature_focus": session_data.get("feature_focus", ""),
        "specific_question": session_data.get("specific_question", ""),
        "avg_satisfaction": session_data.get("avg_satisfaction", 0),
        "deal_breaker_count": session_data.get("deal_breaker_count", 0),
        "persona_count": session_data.get("persona_count", 0),
        "results": session_data.get("results", {}),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "type": "clinic_session",
    }

    # Build searchable text from all persona feedback
    search_text = f"Feature: {doc['feature_focus']}. Question: {doc['specific_question']}. "
    for name, result in doc["results"].items():
        search_text += f"{name} (score {result.get('satisfaction_score', 0)}): "
        search_text += f"{result.get('customer_quote', '')} "
        for like in result.get("likes", []):
            search_text += f"Likes: {like}. "
        for dislike in result.get("dislikes", []):
            search_text += f"Dislikes: {dislike}. "
        for suggestion in result.get("suggestions", []):
            search_text += f"Suggestion: {suggestion}. "

    doc["search_text"] = search_text[:8000]
    doc["embedding"] = _embed(search_text[:2000])

    result = db.clinic_sessions.insert_one(doc)
    return str(result.inserted_id)


def store_design_decision(decision: dict) -> str:
    """Store a design decision with embedding."""
    db = _get_db()
    doc = {
        "feature": decision.get("feature", ""),
        "decision": decision.get("decision", ""),
        "rationale": decision.get("rationale", ""),
        "evidence": decision.get("evidence", ""),
        "author": decision.get("author", ""),
        "status": decision.get("status", "proposed"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "type": "design_decision",
    }

    search_text = f"Feature: {doc['feature']}. Decision: {doc['decision']}. Rationale: {doc['rationale']}. Evidence: {doc['evidence']}"
    doc["search_text"] = search_text
    doc["embedding"] = _embed(search_text[:2000])

    result = db.design_decisions.insert_one(doc)
    return str(result.inserted_id)


def store_feature_spec(spec: dict) -> str:
    """Store a feature spec with embedding."""
    db = _get_db()
    doc = {
        "name": spec.get("name", ""),
        "description": spec.get("description", ""),
        "requirements": spec.get("requirements", []),
        "persona_validation": spec.get("persona_validation", {}),
        "trello_card_id": spec.get("trello_card_id", ""),
        "figma_frame_id": spec.get("figma_frame_id", ""),
        "github_pr_id": spec.get("github_pr_id", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "type": "feature_spec",
    }

    search_text = f"Feature: {doc['name']}. {doc['description']}. Requirements: {', '.join(doc['requirements'])}"
    doc["search_text"] = search_text
    doc["embedding"] = _embed(search_text[:2000])

    result = db.feature_specs.insert_one(doc)
    return str(result.inserted_id)


# --- Search Operations ---

def vector_search(query: str, collection: str = "clinic_sessions",
                  limit: int = 5, filters: dict = None) -> list[dict]:
    """Semantic vector search over Atlas with optional metadata filters."""
    db = _get_db()
    query_embedding = _embed(query)

    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index",
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": limit * 10,
                "limit": limit,
            }
        },
        {
            "$project": {
                "search_text": 1,
                "feature_focus": 1,
                "specific_question": 1,
                "avg_satisfaction": 1,
                "deal_breaker_count": 1,
                "feature": 1,
                "decision": 1,
                "rationale": 1,
                "name": 1,
                "description": 1,
                "type": 1,
                "created_at": 1,
                "score": {"$meta": "vectorSearchScore"},
                "_id": 0,
            }
        },
    ]

    # Add metadata filter if provided
    if filters:
        pipeline[0]["$vectorSearch"]["filter"] = filters

    try:
        results = list(db[collection].aggregate(pipeline))
        return results
    except Exception as e:
        print(f"Vector search error: {e}")
        # Fallback to text search
        return list(db[collection].find(
            {"$text": {"$search": query}},
            {"score": {"$meta": "textScore"}, "_id": 0, "embedding": 0}
        ).sort([("score", {"$meta": "textScore"})]).limit(limit))


def search_all_collections(query: str, limit: int = 5) -> dict:
    """Search across all collections for relevant context."""
    return {
        "clinic_sessions": vector_search(query, "clinic_sessions", limit),
        "design_decisions": vector_search(query, "design_decisions", limit),
        "feature_specs": vector_search(query, "feature_specs", limit),
    }
