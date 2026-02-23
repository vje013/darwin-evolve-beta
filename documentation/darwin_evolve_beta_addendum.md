# DARWIN ENTERPRISE EVOLVE β — Addendum Completion Report

**Vladimir Edouard | The Standardized Data Company**
**February 16, 2026 | Session 2 — Phases 4–5 + autoVendr Scaffold**

---

## What We Built Since Last Report

### Phase 4 — Artifact Generation (Complete ✅)

Five AI-powered document generators that read the full room context — conversation history, graph entities, code files, relationships — and produce structured deliverables stored as versioned nodes in Neo4j.

**Artifact Types:**

| Type | Purpose | Graph Context Used |
|------|---------|-------------------|
| PRD | Product Requirements Document with traceability to designs and code | Entities, relationships, file contents |
| Decision Log | Extracts every decision from chat with rationale, participants, and status | Conversation transcript, entity references |
| Traceability Matrix | Requirement → Design → Code → Test mapping with gap analysis | Full entity graph, file contents, relationships |
| Drift Detection | Compares designs vs implementation, flags divergence from decisions | Figma entities, GitHub entities, file contents, decision history |
| Release Notes | Changelog from PRs, issues, and discussion | PR/Issue entities, commit history |

**How it works:** Each artifact generation call assembles the full room transcript, queries Neo4j for all linked entities and their relationships, fetches up to 20 file contents (with branch labels), and passes everything to the LLM with a type-specific system prompt. The result is stored as an `Artifact` node in Neo4j with `DERIVED_FROM` → Room, `GENERATED_BY` → User, and `REFERENCES` → Entity edges. Subsequent generations of the same type auto-increment the version number and create `SUPERSEDES` chains for audit history.

**Frontend:** New artifacts panel accessible via document icon in room header. Generate tab shows all five types as color-coded cards (PRD green, Decisions gold, Traceability indigo, Drift red, Release Notes blue). Optional instructions field lets users guide generation. History tab lists all previously generated artifacts with version badges. Click any artifact to view in a full dialog with model/cost metadata and referenced entity chips.

### Phase 5 — Graph Visualization (Complete ✅)

Interactive force-directed knowledge graph rendered directly in the right panel using a custom lightweight physics simulation (no D3 dependency required).

**Capabilities:**
- Force-directed layout with repulsion, spring attraction along edges, and center gravity
- Nodes color-coded by entity type (green = Repository, purple = PR, red = Issue, blue = Commit, gray = File, gold = Requirement)
- Node radius scaled by importance (Repository = 10px, Branch = 7px, others = 5px)
- Click any node to inspect: shows name, type, source, truncated ID, and up to 5 connected relationships
- Filter chips across the top to isolate by entity type
- Zoom controls (+/−/center) and scroll-wheel zoom
- Artifact nodes included in the graph with REFERENCES edges to entities they cite
- Panel widens to 420px in graph view for more canvas space
- Node count and edge count displayed in bottom-left corner

**Backend:** New `/rooms/{room_id}/connectors/graph` endpoint returns `{nodes, links}` formatted for D3-style consumption. Queries both Entity nodes and Artifact nodes linked to the room, with all inter-entity relationships.

### autoVendr Scaffold (UI Complete, Agents Pending)

Added the autoVendr entry point to the sidebar — a gradient-bordered button between the header and room list. Clicking it opens a full-screen overlay with two agent cards:

1. **Research Agent** — "Monitors your market and industry. Keeps you up to date on competitors, trends, and emerging signals." (Green, globe icon)
2. **Customer Clinic Agent** — "Reviews your work-in-progress against customer needs. Flags when you're drifting from what users want." (Indigo, people icon)

Both currently show placeholder alerts. The agent backend infrastructure exists from Darwin's heartbeat architecture (EventBridge schedules, Haiku cost gates, Sonnet execution) and can be adapted for Enterprise Evolve rooms.

---

## Current File Inventory Update

**New backend files:**

| File | Purpose |
|------|---------|
| `routes/artifacts.py` | Updated with DriftDetection type, file content injection, model_config fix |
| `routes/connectors.py` | Updated with `/graph` endpoint for D3 visualization data |

**New frontend files:**

| File | Purpose |
|------|---------|
| `components/ArtifactsPanel.jsx` | Generate and view artifacts, type selector, history, viewer dialog |
| `components/GraphPanel.jsx` | Force-directed graph visualization, node inspector, type filtering |
| `components/Sidebar.jsx` | Updated with autoVendr button and agent selection overlay |
| `components/ChatRoom.jsx` | Updated with three panel toggles (connectors, artifacts, graph) |

---

## Room Header — Three Panel Toggles

The room header now has three icons to the right of the model chip:

| Icon | Panel | Width | Color When Active |
|------|-------|-------|-------------------|
| Tree (AccountTree) | Connectors & Entities | 320px | Mint green |
| Document (Description) | Artifacts | 320px | Indigo |
| Bubble (BubbleChart) | Knowledge Graph | 420px | Sky blue |

Only one panel is open at a time. Clicking the active panel's icon closes it.

---

## What's Left

### autoVendr Agents (Next Priority)

The UI scaffold is in place. The agent implementation requires:

**Research Agent:**
- Define a room-level configuration: what industry, what competitors, what signals to track
- Scheduled execution (adapt Darwin's heartbeat pattern): every N hours, the agent searches for market updates using web search or RSS feeds
- Findings posted as system messages to the room, with entities extracted and linked to the graph
- Users can ask `@assistant` about research findings and get answers grounded in the agent's discoveries

**Customer Clinic Agent:**
- Ingests customer interview transcripts, support tickets, or usage data uploaded to the room
- On each run, reviews the current state of linked designs (Figma) and code (GitHub) against customer needs
- Produces a "clinic report" — what's aligned with customer needs, what's drifting, what's missing
- Can be triggered manually or on a schedule after each connector sync

**Shared infrastructure needed:**
- Agent scheduler (cron or EventBridge equivalent for local dev — could use APScheduler or Celery Beat)
- Agent message posting (system messages injected into room via internal API call)
- Agent configuration UI (what to research, which customer data to ingest)

### Customer Input Pipeline

The gap identified in the YC RFS analysis. To complete the "Cursor for PMs" story:

- Upload customer interview recordings → transcription → entity extraction
- Import support tickets from Zendesk/Intercom/Linear
- Ingest product usage analytics (Mixpanel/Amplitude CSV exports)
- All feed into the graph as Customer, PainPoint, FeatureRequest, and UsagePattern entities
- The Research Agent and Customer Clinic Agent synthesize across these sources

### Production Hardening (Phase 6 — Post-Demo)

- PostgreSQL migration
- Redis pub/sub for WebSocket scaling
- Background job queue for connector syncs and agent runs
- GitHub webhook receivers (push-based sync)
- API rate limiting
- Token encryption for stored credentials
- CI/CD with automated tests

### Enterprise Features (Phase 7 — Post-Funding)

- SSO/SAML
- Org admin dashboard
- Room templates
- Audit log export
- Cost budgets and alerts
- Multi-tenant graph isolation

---

## Updated Demo Script (Feb 20)

1. **Login** → Register, show the clean auth screen
2. **Sidebar** → Point out autoVendr button, click it to show the two agents (explain the vision)
3. **Create Room** → "Q1 Platform Redesign", Claude Sonnet
4. **Chat** → Team discussion, show AI responding inline with entity extraction
5. **Switch Models** → Override to GPT-4o for one message, Flash for another
6. **Connect GitHub** → Paste repo + token, watch sync populate the connectors panel
7. **Ask about code** → "@assistant show me code from the X dev branch" — AI reads actual source
8. **Open Graph** → Click bubble icon, show the force-directed entity network, click nodes
9. **Generate PRD** → Open artifacts panel, generate a PRD from the conversation + code
10. **Generate Drift Report** → Show how the AI flags gaps between requirements and implementation
11. **Multi-user** → Incognito tab, second user joins, real-time WebSocket messaging
12. **Cost** → "$0.03 for this entire session" — point out the spend tracker

---

## Cumulative Cost

| Item | Cost |
|------|------|
| LLM calls during all testing (OpenRouter) | ~$0.05 |
| Neo4j Community Edition | $0 |
| Infrastructure (local dev) | $0 |
| **Total to date** | **~$0.05** |

---

*Next: Implement autoVendr Research Agent and Customer Clinic Agent backends, then customer input pipeline for the full "Cursor for PMs" story.*
