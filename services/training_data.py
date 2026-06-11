"""
Darwin Enterprise Evolve Beta — Training Data Generator
Queries Neo4j graph and generates prompt/completion pairs for LoRA fine-tuning via Tinker.

Five query templates from the Tinker backend spec:
1. Design Rationale — why decisions were made
2. Code Understanding — what code does and how it connects
3. Decision History — chronological decision trail
4. Competitive Intel — what we know about competitors/market
5. Traceability — requirement → design → code → test chains
"""
import json
import random
from datetime import datetime, timezone
from services.graph import get_driver


def generate_training_data(min_examples: int = 100) -> list[dict]:
    """
    Generate prompt/completion training pairs from the Neo4j knowledge graph.
    Returns list of {"prompt": str, "completion": str} dicts.
    """
    driver = get_driver()
    examples = []

    with driver.session() as session:
        # --- Template 1: Design Rationale ---
        result = session.run("""
            MATCH (d:Entity {type: 'Decision'})-[r]->(target:Entity)
            OPTIONAL MATCH (d)<-[:FOCUSES_ON]-(room:Room)
            OPTIONAL MATCH (d)-[:HAS_ATTR]->(a:Attribute)-[:HAS_VALUE]->(v:Value)
            WHERE v.valid_to IS NULL
            RETURN d.id AS decision_id, d.name AS decision_name,
                   target.name AS target_name, target.type AS target_type,
                   type(r) AS rel_type,
                   collect(DISTINCT {attr: a.name, val: v.value}) AS attributes,
                   room.name AS room_name
            LIMIT 500
        """)
        for rec in result:
            attrs = {a["attr"]: a["val"] for a in rec["attributes"] if a["attr"]}
            context = f"Decision: {rec['decision_name']}"
            if attrs:
                context += f"\nDetails: {json.dumps(attrs)}"
            context += f"\nRelated: {rec['rel_type']} → {rec['target_name']} ({rec['target_type']})"

            for q in _question_variants_design(rec["decision_name"], rec["target_name"]):
                completion = f"Based on the team's decision records: {rec['decision_name']}."
                if attrs.get("rationale"):
                    completion += f" The rationale was: {attrs['rationale']}."
                completion += f" This decision directly relates to {rec['target_name']} ({rec['target_type']}) via {rec['rel_type']}."
                if attrs.get("status"):
                    completion += f" Current status: {attrs['status']}."
                examples.append({"prompt": q, "completion": completion, "template": "design_rationale"})

        # --- Template 2: Code Understanding ---
        result = session.run("""
            MATCH (f:Entity {type: 'File'})-[r]->(related:Entity)
            OPTIONAL MATCH (f)-[:HAS_ATTR]->(a:Attribute)-[:HAS_VALUE]->(v:Value)
            WHERE v.valid_to IS NULL
            RETURN f.id AS file_id, f.name AS file_name,
                   related.name AS related_name, related.type AS related_type,
                   type(r) AS rel_type,
                   collect(DISTINCT {attr: a.name, val: v.value}) AS attributes
            LIMIT 500
        """)
        for rec in result:
            attrs = {a["attr"]: a["val"] for a in rec["attributes"] if a["attr"]}
            for q in _question_variants_code(rec["file_name"], rec.get("related_name")):
                completion = f"The file {rec['file_name']} is connected to {rec['related_name']} ({rec['related_type']}) through a {rec['rel_type']} relationship."
                if attrs.get("path"):
                    completion += f" Located at: {attrs['path']}."
                if attrs.get("language"):
                    completion += f" Language: {attrs['language']}."
                if attrs.get("description"):
                    completion += f" {attrs['description']}"
                examples.append({"prompt": q, "completion": completion, "template": "code_understanding"})

        # --- Template 3: Decision History ---
        result = session.run("""
            MATCH (d:Decision)
            OPTIONAL MATCH (d)-[:MADE_IN]->(r:Room)
            RETURN d.id AS id, d.content AS content, d.made_by AS made_by,
                   d.timestamp AS timestamp, r.name AS room_name
            ORDER BY d.timestamp DESC
            LIMIT 200
        """)
        decisions = [dict(rec) for rec in result]
        if decisions:
            for q in _question_variants_history():
                completion = "Here's the decision history:\n"
                for i, d in enumerate(decisions[:10]):
                    completion += f"{i+1}. {d['content']}"
                    if d.get("made_by"):
                        completion += f" (by {d['made_by']})"
                    if d.get("room_name"):
                        completion += f" in {d['room_name']}"
                    completion += "\n"
                examples.append({"prompt": q, "completion": completion.strip(), "template": "decision_history"})

        # --- Template 4: Competitive Intel ---
        result = session.run("""
            MATCH (e:Entity)
            WHERE e.type IN ['Competitor', 'Market', 'Trend', 'Industry']
            OPTIONAL MATCH (e)-[r]->(related:Entity)
            OPTIONAL MATCH (e)-[:HAS_ATTR]->(a:Attribute)-[:HAS_VALUE]->(v:Value)
            WHERE v.valid_to IS NULL
            RETURN e.id AS id, e.name AS name, e.type AS type,
                   collect(DISTINCT {rel: type(r), target: related.name}) AS relationships,
                   collect(DISTINCT {attr: a.name, val: v.value}) AS attributes
            LIMIT 200
        """)
        for rec in result:
            attrs = {a["attr"]: a["val"] for a in rec["attributes"] if a["attr"]}
            rels = [r for r in rec["relationships"] if r["target"]]
            for q in _question_variants_competitive(rec["name"], rec["type"]):
                completion = f"{rec['name']} ({rec['type']})"
                if attrs:
                    completion += ". Key attributes: " + "; ".join(f"{k}: {v}" for k, v in attrs.items())
                if rels:
                    completion += ". Related to: " + ", ".join(f"{r['target']} ({r['rel']})" for r in rels[:5])
                completion += "."
                examples.append({"prompt": q, "completion": completion, "template": "competitive_intel"})

        # --- Template 5: Traceability Chains ---
        result = session.run("""
            MATCH path = (req:Entity {type: 'Requirement'})-[*1..3]->(end:Entity)
            WHERE end.type IN ['File', 'Component', 'FigmaFrame', 'FigmaComponent']
            WITH req, end, [n IN nodes(path) | {name: n.name, type: n.type}] AS chain,
                 [r IN relationships(path) | type(r)] AS rels
            RETURN req.name AS req_name, end.name AS end_name, end.type AS end_type,
                   chain, rels
            LIMIT 300
        """)
        for rec in result:
            chain_str = " → ".join(f"{n['name']} ({n['type']})" for n in rec["chain"])
            for q in _question_variants_traceability(rec["req_name"], rec["end_name"]):
                completion = f"Traceability chain: {chain_str}. "
                completion += f"The requirement '{rec['req_name']}' traces through to '{rec['end_name']}' ({rec['end_type']}) "
                completion += f"via: {' → '.join(rec['rels'])}."
                examples.append({"prompt": q, "completion": completion, "template": "traceability"})

        # --- Template 6: General Entity Queries ---
        result = session.run("""
            MATCH (e:Entity)
            OPTIONAL MATCH (e)-[r]->(related:Entity)
            OPTIONAL MATCH (e)-[:HAS_ATTR]->(a:Attribute)-[:HAS_VALUE]->(v:Value)
            WHERE v.valid_to IS NULL
            RETURN e.id AS id, e.name AS name, e.type AS type, e.source AS source,
                   collect(DISTINCT {rel: type(r), target: related.name, target_type: related.type}) AS relationships,
                   collect(DISTINCT {attr: a.name, val: v.value}) AS attributes
            LIMIT 500
        """)
        for rec in result:
            attrs = {a["attr"]: a["val"] for a in rec["attributes"] if a["attr"]}
            rels = [r for r in rec["relationships"] if r["target"]]
            for q in _question_variants_entity(rec["name"], rec["type"]):
                completion = f"{rec['name']} is a {rec['type']} entity (source: {rec['source'] or 'unknown'})."
                if attrs:
                    completion += " Properties: " + "; ".join(f"{k}={v}" for k, v in list(attrs.items())[:5])
                    completion += "."
                if rels:
                    completion += " Connected to: " + ", ".join(
                        f"{r['target']} ({r['target_type']}) via {r['rel']}" for r in rels[:5]
                    ) + "."
                examples.append({"prompt": q, "completion": completion, "template": "entity_query"})

    # Shuffle and return
    random.shuffle(examples)
    return examples


# --- Question Variant Generators ---

def _question_variants_design(decision_name: str, target_name: str) -> list[str]:
    return [
        f"Why did we decide on {decision_name}?",
        f"What was the rationale behind {decision_name}?",
        f"Explain the decision about {decision_name}",
        f"How does {decision_name} relate to {target_name}?",
    ]

def _question_variants_code(file_name: str, related_name: str | None) -> list[str]:
    variants = [
        f"What does {file_name} do?",
        f"Explain the purpose of {file_name}",
        f"How is {file_name} used in the project?",
    ]
    if related_name:
        variants.append(f"How does {file_name} connect to {related_name}?")
    return variants

def _question_variants_history() -> list[str]:
    return [
        "What decisions have we made recently?",
        "Show me the decision history",
        "What are the latest team decisions?",
        "Give me a timeline of decisions",
    ]

def _question_variants_competitive(name: str, entity_type: str) -> list[str]:
    return [
        f"What do we know about {name}?",
        f"Tell me about {name}",
        f"Summarize {name} intelligence",
    ]

def _question_variants_traceability(req_name: str, end_name: str) -> list[str]:
    return [
        f"How does {req_name} trace to implementation?",
        f"What implements {req_name}?",
        f"Show the traceability chain for {req_name}",
        f"How is {end_name} connected to requirements?",
    ]

def _question_variants_entity(name: str, entity_type: str) -> list[str]:
    return [
        f"What is {name}?",
        f"Tell me about {name}",
        f"What do we know about the {entity_type} called {name}?",
    ]
