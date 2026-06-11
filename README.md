# Darwin Enterprise Evolve β

**AI-powered product intelligence platform for automotive HMI teams.**

One workspace where designers, engineers, and PMs operate together. One knowledge graph connecting every Trello card, Figma frame, and GitHub commit. One AI that knows your team's entire product history.

> Built for the Google Cloud Rapid Agent Hackathon 2026
> Gemini 3.5 Flash · MongoDB Atlas Vector Search · Google Cloud Run

---

## The Problem

Automotive HMI teams are broken. Designers live in Figma. Engineers live in GitHub. PMs live in Trello. Nobody shares context. Product managers waste 60-70% of their time stitching information together instead of making decisions.

Then they wait 3 months for a $250K in-person customer clinic to find out their design doesn't work. By then the designers have moved on.

## The Solution

Enterprise Evolve replaces quarterly customer clinics with continuous AI-powered design validation. Upload a CID image, get feedback from 20 simulated customer personas in 2 minutes. Every analysis is stored in MongoDB Atlas with vector embeddings, so the AI gets smarter with every session.

## Demo Video

[Watch the 3-minute demo →](YOUR_YOUTUBE_LINK_HERE)

## Live Deployment

- **Backend:** Google Cloud Run (us-central1)
- **Frontend:** Google Cloud Run (us-central1)
- **Database:** MongoDB Atlas (Cluster007, us-east-1)
- **Vector Search:** Atlas Vector Search with Voyage AI embeddings

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend (Vite)                     │
│  ChatRoom · ClinicAgent · ResearchAgent · GraphPanel · Auth  │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST + WebSocket
┌──────────────────────────┴──────────────────────────────────┐
│                   FastAPI Backend (Python)                    │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │  Bachman AI  │  │ Clinic Agent │  │  Research Agent     │  │
│  │  (Chat +     │  │ (20 Persona  │  │  (arXiv + Claude   │  │
│  │   Context)   │  │  Analysis)   │  │   Newsletter)      │  │
│  └──────┬───────┘  └──────┬───────┘  └────────────────────┘  │
│         │                 │                                   │
│  ┌──────┴─────────────────┴──────────────────────────────┐   │
│  │              MongoDB Atlas Vector Search               │   │
│  │  clinic_sessions · design_decisions · feature_specs    │   │
│  │  Voyage AI embeddings · Semantic retrieval · Memory    │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌────────────┐  ┌──────────┐  ┌──────────┐                 │
│  │   Neo4j     │  │  SQLite  │  │ OpenRouter│                │
│  │ Knowledge   │  │   Auth   │  │  20+ LLMs │                │
│  │   Graph     │  │  & Ops   │  │  Gateway  │                │
│  └──────┬──────┘  └──────────┘  └───────────┘                │
│         │                                                    │
│  ┌──────┴──────────────────────────────────────────────┐     │
│  │              Connectors (GitHub · Figma · Trello)    │     │
│  └─────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘

LLM Layer:
  Gemini 3.5 Flash (Customer Clinic Agent via OpenRouter)
  Claude Sonnet 4 (Research Agent, Data Analyst)
  20+ models selectable per message
```

---

## Key Features

### Customer Clinic Agent (Gemini 3.5 Flash)
Upload any CID/HMI design image. The agent analyzes it from the perspective of 20 diverse customer personas — from a 17-year-old teen driver to a 72-year-old arthritic retiree. Returns satisfaction scores, deal-breaker flags, specific likes/dislikes, and improvement suggestions per persona. Every session auto-stores in MongoDB Atlas with Voyage AI vector embeddings for semantic retrieval.

### MongoDB Atlas as Compounding Team Memory
This is not RAG over static documents. Every clinic session, every design decision, every feature spec lands in Atlas with vector embeddings. When a designer asks "what did customers think about our climate controls?", Atlas Vector Search returns semantically matched sessions ranked by relevance — not keyword matches, but meaning. The team's intelligence compounds with every interaction.

### Knowledge Graph Traceability
Connect GitHub, Figma, and Trello. The Neo4j knowledge graph traces a requirement from a PM's Trello card through a designer's Figma component to an engineer's pull request. Five edge types: Resource, Information, Authority, Constraint, Temporal.

### Multi-Model AI Chat
Bachman, the AI assistant, sits in every chat room with full graph context and MongoDB clinic history. Switch between 20+ models from OpenRouter per message — Gemini, Claude, GPT-4o — with live pricing from OpenRouter's API. Info popover shows context window, input/output cost, and provider for every model.

### Research Agent
Search arXiv for automotive and HMI research papers. Scores papers by relevance. Generates newsletters and podcast transcripts via Claude. Data Analyst subtab lets anyone upload a CSV and query it in natural language.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **AI Reasoning** | Gemini 3.5 Flash (via OpenRouter), Claude Sonnet 4 |
| **Vector Search** | MongoDB Atlas Vector Search (512-dim, cosine similarity) |
| **Embeddings** | Voyage AI (voyage-3-lite, auto-generated on write) |
| **Database** | MongoDB Atlas (clinic data + embeddings), Neo4j (knowledge graph), SQLite (auth + ops) |
| **Backend** | Python, FastAPI, uvicorn, WebSocket |
| **Frontend** | React, Vite, Material UI |
| **Connectors** | GitHub API, Figma API, Trello API |
| **LLM Gateway** | OpenRouter (20+ models, live pricing) |
| **Deployment** | Google Cloud Run (us-central1) |
| **Auth** | JWT + bcrypt |

---

## Setup

### Prerequisites
- Python 3.12+
- Node.js 18+
- Docker (for Neo4j)
- MongoDB Atlas account
- Voyage AI API key
- OpenRouter API key

### Backend

```bash
cd backend
pip install -r requirements.txt

# Create .env
cat > .env << EOF
OPENROUTER_API_KEY=your-key
ANTHROPIC_API_KEY=your-key
GEMINI_API_KEY=your-key
JWT_SECRET=your-secret
NEO4J_URI=bolt://localhost:7688
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/
VOYAGE_API_KEY=your-key
EOF

# Start Neo4j
docker-compose up -d

# Start backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`

### MongoDB Atlas Setup

1. Create a free M0 cluster on [cloud.mongodb.com](https://cloud.mongodb.com)
2. Create database `darwin_evolve` with collections: `clinic_sessions`, `design_decisions`, `feature_specs`
3. Create Atlas Vector Search index on each collection:

```json
{
  "fields": [{
    "type": "vector",
    "path": "embedding",
    "numDimensions": 512,
    "similarity": "cosine"
  }]
}
```

---

## How the Agent Loop Works

```
Designer uploads CID image
        │
        ▼
┌─────────────────────────────┐
│  Gemini 3.5 Flash analyzes  │
│  from 20 customer personas  │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  Results + Voyage embedding │
│  stored in MongoDB Atlas    │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  Next query triggers Atlas  │
│  Vector Search — retrieves  │
│  relevant past sessions     │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  Bachman synthesizes clinic │
│  history + graph context    │
│  into design recommendation │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  Decision stored back in    │
│  Atlas — loop compounds     │
└─────────────────────────────┘
```

---

## Impact

- Subaru spends $1M/year on HMI customer clinics. Enterprise Evolve replaces that with a 2-minute AI analysis at $0.50 in API costs.
- 40+ automotive OEMs in America run similar programs.
- Chinese, Korean, and Vietnamese OEMs entering the US market have zero customer intelligence infrastructure. Enterprise Evolve is the American consumer intelligence layer.
- TAM extends beyond automotive to any screen-based product team needing continuous customer validation.

---

## What Makes This Different

Most hackathon entries use MongoDB as a RAG store over static documents. Enterprise Evolve uses Atlas as a **compounding team intelligence layer** — every clinic session, every design decision, every feature iteration lands back in Atlas with vector embeddings and makes the next query smarter. The team graph (Trello → Figma → GitHub → customer signals) as a MongoDB document structure with vector search over it is architecturally novel.

This isn't a prototype. The founder ran a version of this at Subaru for over a year on production HMI decisions.

---

## Team

**Vladimir Edouard** — CEO, Darwin Adaptive Systems LLC. R&D Software Engineer at Subaru (HMI Advanced Technology team). Built Enterprise Evolve because his team needed it.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
