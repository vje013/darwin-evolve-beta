# DARWIN ENTERPRISE EVOLVE β — Build Completion Report

**Vladimir Edouard | The Standardized Data Company**
**February 15–16, 2026 | Local Development Environment**

---

## Executive Summary

Over two intensive build sessions (Feb 15–16), we took Darwin Enterprise Evolve from a spec document to a functional collaborative AI platform. The system now supports multi-user chat rooms with real-time WebSocket messaging, an AI participant that reads from a live Neo4j knowledge graph, GitHub integration that syncs branches/PRs/issues/code into the graph, and a Figma connector ready for activation. The AI can see and discuss actual source code from any branch in a connected repository.

**Total Cost Incurred:** ~$0.03 in LLM calls during testing (OpenRouter → Claude/GPT-4o/Gemini)
**Total Entities in Graph:** 229 (across PRs, issues, commits, branches, files, chat extractions)
**Backend:** 17 Python files across FastAPI + Neo4j + SQLite
**Frontend:** 7 React components + 1 custom hook

---

## What We Built

### Phase 0 — Scaffold (Complete ✅)

Stood up the entire project skeleton from scratch:

- **Backend:** FastAPI with uvicorn, SQLite for operational data (users, rooms, messages, connectors), Neo4j Community Edition (Docker) for the knowledge graph
- **Frontend:** React + Vite + Material UI with JetBrains Mono / DM Sans typography, dark theme with Darwin's mint green (`#6ee7b7`) and indigo (`#818cf8`) accent palette
- **Infrastructure:** Docker Compose for Neo4j (ports 7475 browser / 7688 bolt), `.env` configuration, CORS setup for React dev server
- **Auth:** JWT-based registration/login with bcrypt password hashing
- **Port conflict resolution:** Remapped Neo4j to avoid collision with existing installations (7474→7475, 7687→7688)

### Phase 1 — Auth + Rooms (Complete ✅)

- User registration and login with JWT tokens (24-hour expiry)
- Room CRUD with member management
- ACL roles: owner, admin, member, viewer — enforced at every endpoint
- Per-room default model selection from OpenRouter catalog
- Room spend tracking (aggregated from model invocation table)

### Phase 2 — Chat + AI + Extraction (Complete ✅)

- `@assistant` mention detection triggers LLM invocation via OpenRouter
- Per-message model override (switch between Sonnet, Haiku, GPT-4o, Gemini mid-conversation)
- Conversation history (last 20 messages) passed as context to each AI call
- **Entity extraction pipeline:** Every AI response is analyzed for entities → merged into Neo4j with five-edge-type schema (RESOURCE, INFORMATION, AUTHORITY, CONSTRAINT, TEMPORAL)
- **Graph context injection:** Before each AI response, the system queries Neo4j for room-linked entities and recent decisions, injecting them into the system prompt
- **WebSocket real-time messaging:** `ConnectionManager` tracks connections per room, broadcasts messages to all connected clients, supports online presence indicators, "AI thinking" state propagation, and auto-reconnect with 30-second ping keepalive
- **Cost tracking:** Every LLM invocation logged with model, tokens in/out, cost — displayed as running total in room header
- **Full audit trail:** Every action (register, room create, message send, AI invoke, connector link) logged as AuditEvent nodes in Neo4j
- **UI polish:** Timestamps on every message (local timezone), markdown stripping for AI responses, clickable entity chips, cost consolidation in header

### Phase 3 — Connectors (Complete ✅)

**GitHub Connector:**
- Connect any GitHub repo via personal access token
- **Branch-aware sync:** Fetches all branches (not just main/HEAD), creates Branch entities linked to Repository
- **Full file tree per branch:** Walks each branch's git tree, filters to code files by extension, skips vendor/build directories
- **Source code storage:** Uses Git Blobs API with base64 decoding to fetch actual file contents (not GitHub HTML), stores up to 10KB per file as EAV attributes in Neo4j
- **PR/Issue/Commit sync:** Pulls open and closed PRs, issues (with labels, authors, timestamps), recent commits — all as typed Entity nodes with BELONGS_TO relationships
- **AI code awareness:** File contents injected into AI context with branch labels — the assistant can read, discuss, and reference actual source code from any branch
- **Rate limiting:** Caps file fetches per branch (30 for ≤5 branches, 15 for more) to stay within GitHub API limits

**Figma Connector:**
- Scaffolded and ready — fetches file metadata, page structure, frames, components, version history
- Creates FigmaFile → FigmaPage → FigmaFrame/FigmaComponent entity hierarchy
- Awaiting a Figma file key + PAT to test live

**Connector UI Panel:**
- Toggleable right-side panel (tree icon in room header)
- Add connector dialog with platform selector (GitHub/Figma), token input, helper text
- Connected integrations shown as green chips with click-to-sync and X-to-delete
- Entity list with source filtering (All / github / chat_extraction), type badges, relationship display
- Sync result alerts with counts (branches, PRs, issues, commits, files)
- Entity count and connector count in footer

---

## Technical Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌──────────────────┐
│  React Frontend │────▶│  FastAPI      │────▶│  Neo4j Graph     │
│  (Vite :3000)   │◀────│  (:8000)      │◀────│  (Docker :7688)  │
│                 │ WS  │              │     │                  │
│  - AuthScreen   │     │  - Auth/JWT   │     │  Entity nodes    │
│  - Sidebar      │     │  - Rooms      │     │  EAV attributes  │
│  - ChatRoom     │     │  - Messages   │     │  5 edge types    │
│  - ConnectorsPanel    │  - Connectors │     │  Audit events    │
│  - useWebSocket │     │  - Artifacts  │     │  Model invocations│
└─────────────────┘     │  - WS Manager │     └──────────────────┘
                        │              │
                        │  ┌───────────┤     ┌──────────────────┐
                        │  │ Services  │────▶│  SQLite           │
                        │  │ - LLM     │     │  (darwin.db)      │
                        │  │ - Graph   │     │  users, rooms,    │
                        │  │ - Extractor│    │  messages, members│
                        │  │ - Audit   │     │  connectors,      │
                        │  │ - GitHub  │     │  invocations      │
                        │  │ - Figma   │     └──────────────────┘
                        │  │ - WS Mgr  │
                        │  └───────────┤     ┌──────────────────┐
                        │              │────▶│  OpenRouter       │
                        └──────────────┘     │  Claude Sonnet    │
                                             │  Claude Haiku     │
                                             │  GPT-4o / Gemini  │
                                             └──────────────────┘
```

### File Inventory

**Backend (17 files):**

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app, lifespan, CORS, WebSocket endpoint, auth routes, health check |
| `auth.py` | JWT encode/decode, registration, login, bcrypt, role checking |
| `db.py` | SQLite init, schema (7 tables), connection manager |
| `routes/rooms.py` | Room CRUD, member management, model config |
| `routes/messages.py` | Message send, @assistant detection, AI context assembly, WS broadcast |
| `routes/artifacts.py` | Artifact generation stubs (Phase 4) |
| `routes/connectors.py` | Connector CRUD, sync dispatch, entity listing |
| `services/llm.py` | OpenRouter gateway, model routing, cost tracking |
| `services/graph.py` | Neo4j driver, entity merge, EAV attributes, context queries, file content retrieval |
| `services/extractor.py` | Entity extraction from conversations via LLM |
| `services/audit.py` | Audit event logging to Neo4j |
| `services/ws_manager.py` | WebSocket connection tracking, per-room broadcast |
| `services/github_connector.py` | GitHub API: branches, PRs, issues, commits, file tree, blob content |
| `services/figma_connector.py` | Figma API: files, pages, frames, components, versions |
| `docker-compose.yml` | Neo4j Community with remapped ports |
| `requirements.txt` | Python dependencies |
| `.env` | API keys, Neo4j credentials, JWT config |

**Frontend (8 files):**

| File | Purpose |
|------|---------|
| `main.jsx` | React root, Material UI dark theme setup |
| `App.jsx` | Auth gate, layout with sidebar + chat room |
| `api/client.js` | API client with token management, all endpoint functions |
| `components/AuthScreen.jsx` | Login/register form |
| `components/Sidebar.jsx` | Room list, create room dialog, model selector |
| `components/ChatRoom.jsx` | Message list, input, model override, WS integration, panel toggle |
| `components/ConnectorsPanel.jsx` | GitHub/Figma connector UI, entity list, sync controls |
| `hooks/useWebSocket.js` | WebSocket hook with auto-reconnect, ping keepalive |

---

## What Needs Fixing

### Known Bugs

1. **GitHub HTML artifacts in repos:** Repos with saved GitHub web pages (`.js`, `.css` from "Save page as...") get synced as code files. Need to add a filter that skips files inside directories containing `_files/` patterns, or files where content starts with common HTML/webpack signatures.

2. **AI entity citation garbling:** The assistant sometimes confuses branch entity names with file entity names in its citations. The entity names include full paths which pollute the context. Solution: shorten entity display names in the context block (show `branch:filename` not the full entity ID).

3. **File content context limit:** Currently fetches 30 files max for AI context. Repos with multiple branches can have hundreds of files. Need intelligent selection — prioritize files mentioned in conversation, recently modified files, or files the user asks about specifically.

4. **Connector delete route mismatch:** The frontend calls `/connectors/connectors/{id}` (double "connectors" in path) due to the router prefix. Verify the DELETE endpoint path matches.

5. **Duplicate connectors possible:** No uniqueness check when adding a connector — user can add the same GitHub repo twice. Add a check for existing connector with same type + config.

6. **WebSocket same-user exclusion removed:** We set `exclude_user_id=None` to fix multi-tab messaging, but this means the sender sees their own message twice (once from HTTP response, once from WS). The frontend deduplicates by `message_id`, but there's a brief flash. Proper fix: exclude by WebSocket connection ID, not user ID.

### Technical Debt

- **No tests.** Zero unit or integration tests exist. Critical paths (auth, message flow, entity extraction, GitHub sync) should have test coverage before demo.
- **No rate limiting on API endpoints.** A bad actor could spam messages or trigger expensive AI calls.
- **Secrets in .env file.** GitHub PATs stored in SQLite `connectors.config` column as JSON. Should be encrypted at rest.
- **No pagination.** Message list loads all messages up to limit. Entity list in panel loads everything. Will break with scale.
- **SQLite for production.** Fine for beta/demo, but need PostgreSQL migration path for multi-user deployment.

---

## What's Next

### Phase 4 — Artifact Generation (Next Up)

AI-powered document generation from graph context:

- **PRD Generator:** "Generate a PRD for this room" → AI reads all entities, decisions, discussions → produces a structured product requirements document
- **Decision Log:** Automatically tracks decisions made in chat (detected by keywords like "let's go with", "decided", "agreed") → generates a decision log artifact with rationale and participants
- **Traceability Matrix:** Connects requirements → designs → code → tests using the graph relationships → generates a matrix showing coverage gaps
- **Drift Detection:** Compares Figma designs against code implementations, flags when designs changed but code didn't (or vice versa)

### Phase 5 — Graph Visualization

Interactive graph visualization in the right panel:

- D3.js or Cytoscape.js force-directed graph of room entities
- Click entity → see attributes, relationships, source
- Filter by type, source, date range
- Highlight paths between entities (e.g., "show me everything connecting this Issue to this PR")

### Phase 6 — Production Hardening

- PostgreSQL migration (keep SQLite for local-first story)
- Redis for WebSocket pub/sub (current in-memory manager doesn't scale past single process)
- Background job queue for connector syncs (currently blocks the HTTP response)
- Webhook receivers for GitHub (push-based instead of pull-based sync)
- API rate limiting and abuse prevention
- Token encryption for stored connector credentials
- CI/CD pipeline with automated testing

### Phase 7 — Enterprise Features

- SSO/SAML integration
- Org-level admin dashboard
- Room templates (pre-configured connectors + models for common workflows)
- Audit log export (compliance)
- Cost budgets and alerts per room/org
- Multi-tenant graph isolation

---

## Demo Script (for Feb 20 Ship Date)

1. **Login** → Show the auth screen, register a new user
2. **Create Room** → "Q1 Platform Redesign", default model Claude Sonnet
3. **Chat** → Send a few messages, show the AI responding inline
4. **Switch Models** → Override to GPT-4o for one message, switch back
5. **Connect GitHub** → Paste repo + token, watch entities populate in the right panel
6. **Ask about code** → "@assistant what branches exist?" → "@assistant show me the code in newsTry.py on the X dev branch"
7. **Show entity chips** → Point out the extracted entities under AI responses
8. **Show graph** → Open Neo4j browser, show the entity network
9. **Multi-user** → Open incognito, second user joins same room, messages appear in real-time
10. **Cost** → Point out the spend tracker in the header — "This entire session cost $0.03"

---

## Cost Summary

| Item | Cost |
|------|------|
| LLM calls during testing (OpenRouter) | ~$0.03 |
| Neo4j Community Edition | $0 (open source) |
| Infrastructure (local dev) | $0 |
| **Total** | **~$0.03** |

---

## Key Decisions Made

1. **OpenRouter over direct API:** Gives us model switching (Claude/GPT/Gemini) without multiple API integrations. Single gateway, unified billing.
2. **Neo4j over Neptune for local:** Neptune requires AWS VPC. Neo4j Community runs in Docker locally, same Cypher query language, easier to demo. Production can use either.
3. **SQLite + Neo4j dual store:** Operational data (users, auth, messages) in SQLite for simplicity. Knowledge graph (entities, relationships, attributes) in Neo4j for traversal queries. Clean separation.
4. **EAV temporal pattern:** Entity-Attribute-Value with `valid_from`/`valid_to` on values. Lets us track how entity attributes change over time — critical for drift detection.
5. **WebSocket for real-time:** Polling would work but breaks the collaborative story. WebSocket with auto-reconnect gives Slack-like UX.
6. **Git Blobs API for content:** GitHub's Contents API returns rendered HTML from the CDN. Blobs API returns base64-encoded raw content reliably. Learned this the hard way.

---

*Next session: Phase 4 artifact generation, then graph visualization, then prep for Feb 20 ship.*
