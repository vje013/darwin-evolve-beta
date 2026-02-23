# Darwin Enterprise Evolve β

Collaborative AI chat with graph-backed traceability. The wedge product for Darwin Enterprise Evolve.

## What This Is

A multi-user chat platform where engineering teams collaborate with AI. Every conversation silently builds a knowledge graph (Neo4j) that connects requirements, designs, decisions, PRs, and releases. The graph is the product — the AI is just the interface to it.

**Enterprise Evolve DNA**: Every relationship in the graph uses the five-edge-type schema (Resource, Information, Authority, Constraint, Temporal) and the EAV temporal pattern, so when this scales to a full organizational ontology, no migration is needed.

## Quick Start

### Prerequisites
- Docker Desktop
- Python 3.11+
- Node.js 18+

### Setup

```bash
# 1. Clone and enter
cd darwin-evolve-beta

# 2. Set up environment
cp .env.example .env
# Edit .env and add your OpenRouter API key

# 3. Start Neo4j
docker-compose up -d

# 4. Start backend (Terminal 1)
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 5. Start frontend (Terminal 2)
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 — register an account, create a room, and start chatting.

Neo4j Browser at http://localhost:7474 (neo4j/darwin2026) — watch the graph grow.

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  React UI    │────▶│  FastAPI      │────▶│  OpenRouter   │
│  (Material3) │     │  (Python)     │     │  (LLM Gateway)│
└──────────────┘     └──────┬───────┘     └──────────────┘
                            │
                     ┌──────┴───────┐
                     │              │
               ┌─────▼─────┐ ┌─────▼─────┐
               │  SQLite    │ │  Neo4j    │
               │  (ops data)│ │  (graph)  │
               └───────────┘ └───────────┘
```

- **SQLite**: Users, rooms, messages, invocations (operational data)
- **Neo4j**: Entities, relationships, audit events, artifacts, decisions (the graph)
- **OpenRouter**: Model-agnostic LLM gateway (Claude, GPT, Gemini)

## Key Features

- **Multi-user rooms** with role-based access (owner/admin/member/viewer)
- **@assistant** mention triggers AI with graph context
- **Per-room model selection** via OpenRouter (switch models mid-conversation)
- **Per-message model override** (use GPT for code, Claude for writing)
- **Automatic entity extraction** — graph grows as a byproduct of chat
- **Artifact generation** — PRDs, decision logs, traceability matrices
- **Full audit trail** — every action is a node in Neo4j

## API Routes

### Auth
- `POST /register` — Create account
- `POST /login` — Sign in, get JWT
- `GET /me` — Current user

### Rooms
- `POST /rooms` — Create room with model selection
- `GET /rooms` — List your rooms
- `GET /rooms/:id` — Room details + spend
- `PUT /rooms/:id/settings` — Update model, budget, etc.
- `POST /rooms/:id/members` — Add member by email
- `DELETE /rooms/:id/members/:uid` — Remove member

### Messages
- `GET /rooms/:id/messages` — Get messages
- `POST /rooms/:id/messages` — Send message (detects @assistant)

### Artifacts
- `POST /rooms/:id/artifacts/generate` — Generate PRD, decisions, etc.
- `GET /rooms/:id/artifacts` — List artifacts
- `GET /rooms/:id/artifacts/:aid` — Get artifact content

### Connectors
- `POST /rooms/:id/connectors` — Link GitHub/Figma
- `POST /rooms/:id/connectors/entities` — Manually link entity to room

### Spend
- `GET /spend` — Spend by room and model

## Graph Schema (Enterprise Evolve Compatible)

### Edge Types
| Type | Meaning |
|------|---------|
| RESOURCE | Material/capital flow |
| INFORMATION | Data/signal flow |
| AUTHORITY | Decision rights, approvals |
| CONSTRAINT | Bottlenecks, dependencies |
| TEMPORAL | Sequencing, scheduling |

### EAV Pattern
```
(Entity)-[:HAS_ATTR]->(Attribute)-[:HAS_VALUE]->(Value {value, dtype, source, valid_from, valid_to})
```

## Build Phases

- [x] Phase 0: Scaffold (Docker, FastAPI, React, Neo4j)
- [ ] Phase 1: Auth + Rooms + Members (Days 1-2)
- [ ] Phase 2: Chat + AI + Entity Extraction (Days 3-4)
- [ ] Phase 3: Connectors + Context-Aware AI (Days 5-6)
- [ ] Phase 4: Artifacts + Drift Detection (Days 7-8)
- [ ] Phase 5: Polish + Demo Prep (Days 9-10)
