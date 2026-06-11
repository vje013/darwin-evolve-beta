# Darwin Enterprise Evolve β

**AI-powered product intelligence platform for automotive HMI teams.**

One workspace where designers, engineers, and PMs operate together. One knowledge graph connecting every Trello card, Figma frame, and GitHub commit. One AI that knows your team's entire product history — grounded in physics.

> Built for the Google Cloud Rapid Agent Hackathon 2026
> Gemini 3.5 Flash · NVIDIA Cosmos Reason 2B · MongoDB Atlas Vector Search · Google Cloud Run

---

## The Problem

Automotive HMI teams are broken. Designers live in Figma. Engineers live in GitHub. PMs live in Trello. Nobody shares context. Product managers waste 60-70% of their time stitching information together instead of making decisions.

Then they wait 3 months for a $250K in-person customer clinic to find out their design doesn't work. By then the designers have moved on.

## The Solution

Enterprise Evolve replaces quarterly customer clinics with continuous AI-powered design validation. Upload a CID image, get physics-grounded feedback from 20 simulated customer personas through a structured 14-step usability protocol — in minutes, not months. Every session is stored in MongoDB Atlas with vector embeddings, so the AI gets smarter with every session.

## Demo Video

[Watch the 3-minute demo →](YOUR_YOUTUBE_LINK_HERE)

## Live Deployment

- **Backend:** Google Cloud Run (us-central1)
- **Frontend:** Google Cloud Run (us-central1)
- **Physics Grounding:** NVIDIA Cosmos Reason 2B on Google Colab GPU
- **Database:** MongoDB Atlas (Cluster007, us-east-1)
- **Vector Search:** Atlas Vector Search with Voyage AI embeddings (512-dim, cosine)

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
│  ┌─────────────────────────────────────────────────────────┐ │
│  │            Structured Clinic Protocol Engine             │ │
│  │  14-step PROMPTER_SPINE · Non-leading facilitation      │ │
│  │  Multi-turn transcript · Score extraction                │ │
│  └────────┬────────────────────────┬───────────────────────┘ │
│           │                        │                         │
│  ┌────────▼────────┐    ┌─────────▼──────────┐              │
│  │  NVIDIA Cosmos   │    │  Gemini 3.5 Flash  │              │
│  │  Reason 2B       │    │  (20 Personas)     │              │
│  │  Physics Ground  │    │  via OpenRouter     │              │
│  │  (Colab GPU)     │    │                    │              │
│  └────────┬────────┘    └─────────┬──────────┘              │
│           │                        │                         │
│           ▼                        ▼                         │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              MongoDB Atlas Vector Search                 │ │
│  │  clinic_sessions · design_decisions · feature_specs      │ │
│  │  Voyage AI embeddings · Semantic retrieval · Memory      │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─────────────┐  ┌──────────┐  ┌───────────┐               │
│  │  Gemini 2.5  │  │  Neo4j   │  │  SQLite   │               │
│  │  Flash ADK   │  │ Knowledge│  │  Auth &   │               │
│  │  Agent       │  │  Graph   │  │  Ops      │               │
│  └──────┬──────┘  └────┬─────┘  └───────────┘               │
│         │               │                                    │
│  ┌──────┴───────────────┴──────────────────────────────┐     │
│  │         Connectors (GitHub · Figma · Trello)         │     │
│  └─────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
```

---

## Key Features

### Physics-Grounded Customer Clinic (Cosmos Reason 2B + Gemini)

Upload any CID/HMI design image. NVIDIA Cosmos Reason 2B analyzes the physical properties first — viewing geometry, touch target sizing against ISO 15008, reachability from the driver's H-point, glare susceptibility, motion readability at highway speed. Then Gemini 3.5 Flash runs each of 20 diverse customer personas through a structured 14-step usability protocol, grounded in those physical constraints.

The 72-year-old arthritic retiree doesn't just say "buttons are too small." She says it because Cosmos measured the touch targets at 8mm — below the ISO 15008 10mm minimum — and the reach distance exceeds her comfortable envelope.

### Structured Usability Protocol (PROMPTER_SPINE)

Not a single-shot prompt. A 14-step facilitated session per persona:
1. Introduction and expectation setting
2. First impression (no touching)
3. Free exploration
4. Rate: Clear, Simple, Modern, Seamless, Personal (1-10 each)
5. Task: Find dark mode
6. Task: Navigate home
7. Layout opinion
8. Dealbreakers
9. Likes
10. Closing thoughts

Non-leading facilitation by design. Running transcript as context. Synthetic timestamps. The output reads like a real usability clinic transcript, not a JSON blob.

### ADK Agent with MongoDB Atlas Tools

The Gemini 2.5 Flash ADK agent has four MongoDB tools: search_clinic_history, search_design_decisions, search_feature_specs, store_design_decision. When a designer asks "what did customers think about the sound equalizer?", the agent searches Atlas Vector Search, synthesizes findings with cited customer evidence, and stores the design recommendation back in Atlas. Multi-step loop confirmed: 3 turns (search → retrieve → synthesize).

### MongoDB Atlas as Compounding Team Memory

This is not RAG over static documents. Every clinic session, every design decision, every feature spec lands in Atlas with Voyage AI vector embeddings auto-generated on write. The team's intelligence compounds with every interaction. Semantic retrieval by feature area, persona segment, and satisfaction level.

### Knowledge Graph Traceability

Connect GitHub, Figma, and Trello. The Neo4j knowledge graph traces a requirement from a PM's Trello card through a designer's Figma component to an engineer's pull request. Five edge types: Resource, Information, Authority, Constraint, Temporal.

### Custom Model Training

Once the knowledge graph is dense enough (2,000+ relationships, 500+ cross-type edges), one click trains a Llama 3.2-3B LoRA model on the team's own data via Tinker. The trained model redeploys into the chat. Every recommendation comes from a model that has read every document, decision, and clinic session your team has ever run through the system.

### Multi-Model AI Chat

Bachman, the AI assistant, sits in every chat room with full graph context and MongoDB clinic history. Switch between 20+ models from OpenRouter per message — Gemini, Claude, GPT-4o — with live pricing. Info popover shows context window, input/output cost, and provider for every model.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Physics Grounding** | NVIDIA Cosmos Reason 2B (Google Colab GPU via Cloudflare tunnel) |
| **AI Reasoning** | Gemini 3.5 Flash + Gemini 2.5 Flash (via OpenRouter) |
| **ADK Agent** | Google ADK pattern with Gemini function calling |
| **Vector Search** | MongoDB Atlas Vector Search (512-dim, cosine similarity) |
| **Embeddings** | Voyage AI (voyage-3-lite, auto-generated on write) |
| **Database** | MongoDB Atlas (clinic data + embeddings), Neo4j (knowledge graph), SQLite (auth + ops) |
| **Custom Training** | Tinker (Llama 3.2-3B LoRA, 2,454 examples, 0.0195 loss) |
| **Backend** | Python, FastAPI, uvicorn, WebSocket |
| **Frontend** | React, Vite, Material UI |
| **Connectors** | GitHub API, Figma API, Trello API |
| **LLM Gateway** | OpenRouter (20+ models, live pricing) |
| **Deployment** | Google Cloud Run (us-central1) |

---

## How the Agent Loop Works

```
Designer uploads CID image
        │
        ▼
┌─────────────────────────────────┐
│  NVIDIA Cosmos Reason 2B        │
│  Physics analysis: viewing      │
│  geometry, reachability, touch  │
│  targets, glare, ISO compliance │
└──────────────┬──────────────────┘
               │ physical constraints
               ▼
┌─────────────────────────────────┐
│  Gemini 3.5 Flash               │
│  14-step structured protocol    │
│  per persona, grounded in       │
│  Cosmos physics output          │
└──────────────┬──────────────────┘
               │ transcript + scores
               ▼
┌─────────────────────────────────┐
│  MongoDB Atlas + Voyage AI      │
│  Auto-embed + store session     │
│  Vector index for retrieval     │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  ADK Agent (Gemini 2.5 Flash)   │
│  Searches Atlas for relevant    │
│  past sessions, synthesizes     │
│  recommendation, stores back    │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  Decision in Atlas — loop       │
│  compounds. Next query is       │
│  smarter than the last.         │
└─────────────────────────────────┘
```

---

## Setup

### Prerequisites
- Python 3.12+
- Node.js 18+
- Docker (for Neo4j)
- MongoDB Atlas account
- Voyage AI API key
- OpenRouter API key
- Google Colab (for Cosmos Reason GPU inference)

### Backend

```bash
cd backend
pip install -r requirements.txt

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
COSMOS_API_URL=your-colab-tunnel-url
EOF

docker-compose up -d
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`

### Cosmos Reason (Google Colab)

1. Open the Cosmos Reason notebook in Google Colab with T4 GPU runtime
2. Run cells to load nvidia/Cosmos-Reason2-2B and start the Flask API
3. Copy the Cloudflare tunnel URL to your backend `.env` as `COSMOS_API_URL`

### MongoDB Atlas

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

## Impact

- Subaru spends $1M/year on HMI customer clinics. Enterprise Evolve replaces that with physics-grounded AI analysis at $0.50 per session.
- 40+ automotive OEMs in America run similar programs.
- Chinese, Korean, and Vietnamese OEMs entering the US market have zero customer intelligence infrastructure. Enterprise Evolve is the American consumer intelligence layer.
- TAM extends beyond automotive to any screen-based product team needing continuous customer validation.

---

## What Makes This Different

Every other submission uses MongoDB as a document store with vector search bolted on. Enterprise Evolve uses Atlas as a **compounding team intelligence layer** where every clinic session, design decision, and feature iteration lands with vector embeddings and makes the next query smarter.

Every other submission uses an LLM to guess about the physical world. Enterprise Evolve uses **NVIDIA Cosmos Reason 2B** — a physics-native vision model — to ground every persona response in measured ergonomic constraints. The personas don't hallucinate about button sizes. They react to ISO-referenced physical measurements.

This isn't a prototype. The founder ran a version of this at Subaru for over a year on production HMI decisions.

---

## Team

**Vladimir Edouard** — CEO, Darwin Adaptive Systems LLC. R&D Software Engineer at Subaru (HMI Advanced Technology team). Built Enterprise Evolve because his team needed it.

**Brandon Chen** — COO, Darwin Adaptive Systems LLC.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
