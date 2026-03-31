# NEXUS OS — Multi-Agent Productivity Assistant

> **Google Cloud Gen AI Academy APAC 2025 Hackathon**
> Problem: Multi-Agent AI system for task, schedule, and information management

---

## What is NEXUS?

NEXUS is a **Multi-Agent Productivity OS** that coordinates specialist AI agents — each owning a domain — to manage your tasks, calendar, research, and memory in a unified flow.

A single natural-language prompt triggers a swarm of specialists that run in **parallel phases**, each writing to a shared Blackboard, persisting to Supabase, and streaming live traces back to the UI via SSE.

---

## Architecture

```
User Prompt
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│  SwarmEngine (Orchestrator)                              │
│  • Gemini 2.0 Flash → dynamic phase plan               │
│  • asyncio.gather → parallel specialist execution       │
└──────────┬──────────────────────────────────────────────┘
           │ Shared Blackboard (dot-notation K/V)
    ┌──────┼──────────────────────┐
    │      │                      │
 Phase 1 (parallel)           Phase 2 (parallel)
 Atlas  Mnemo              Sage   Chrono
    │      │                      │
    └──────┼──────────────────────┘
           │
    ┌──────▼──────────────────────┐
    │  4-Layer Memory Hierarchy   │
    │  L1: Blackboard (reactive)  │
    │  L2: JSON disk (session)    │
    │  L3: Supabase context_items │
    │  L4: pgvector semantic vault│
    └─────────────────────────────┘
           │
    SSE stream → Frontend D3 graph → Live trace UI
```

### Agents

| Agent | Role | MCP Tools (Real APIs) |
|-------|------|----------------------|
| **Orchestrator** | Phase planning, swarm consensus | Gemini 2.0 Flash (Google AI) |
| **Atlas** | Web intelligence & research | Tavily Search, Wikipedia, Web Scraper |
| **Chrono** | Calendar & scheduling | Google Calendar API |
| **Sage** | Knowledge architecture | Notion API, Google Drive |
| **Mnemo** | 4-layer semantic recall | Supabase (pgvector) |
| **Tasks** | Task management | Firestore (in-memory) |
| **Goals** | 90-day roadmapping | — |
| **Briefing** | Daily context synthesis | OpenWeatherMap, wttr.in (free fallback) |
| **Analytics** | Productivity metrics | Python Executor |
| **Toolbox** | Utility & External APIs | **Finance**: CoinGecko (crypto), ExchangeRate-API (currency), Alpha Vantage (stocks) <br> **News**: HackerNews Algolia <br> **Info**: REST Countries, Free Dictionary API <br> **Maps**: OpenStreetMap, OpenRouteService |

### Real API Sources (from public-apis)

All live data is sourced from **free, public APIs** (no auth required for most):

- **Crypto**: [CoinGecko](https://www.coingecko.com/en/api) — Live prices for 10,000+ coins
- **Currency**: [ExchangeRate-API](https://www.exchangerate-api.com/) — 160+ currencies
- **Weather**: [OpenWeatherMap](https://openweathermap.org/api) + [wttr.in](https://wttr.in/) (free fallback)
- **News**: [HackerNews API](https://hn.algolia.com/) via Algolia
- **Countries**: [REST Countries](https://restcountries.com/) — 250+ countries
- **Dictionary**: [Free Dictionary API](https://dictionaryapi.dev/)
- **Wikipedia**: MediaWiki API
- **Search**: Tavily, Brave Search (optional)

---

## Quick Start

```bash
# 1. Clone and set up
git clone <repo-url>
cd nexus-hackathon
./setup.sh

# 2. Configure (optional — defaults to demo mode)
vim nexus/.env   # add GOOGLE_API_KEY, SUPABASE_*, TAVILY_API_KEY

# 3. Run
./run.sh

# 4. Open
open http://localhost:8000          # Landing page (scroll story)
open http://localhost:8000/studio   # Mission Control (send prompts)
open http://localhost:8000/memory   # Memory vault
open http://localhost:8000/docs     # API docs
```

### Demo mode (no keys required)
Set `DEMO_MODE=true` in `nexus/.env` (the default). All agents return structured fixture responses. The swarm graph, SSE streaming, Blackboard state, and all four memory layers work without any external API keys.

### Live mode
Set `DEMO_MODE=false` and provide:
- `GOOGLE_API_KEY` — Gemini 2.0 Flash (planning + embeddings)
- `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` — memory persistence
- `TAVILY_API_KEY` — Atlas web search (optional; falls back to DuckDuckGo)

---

## Core Requirements ✓

| Requirement | Implementation |
|-------------|----------------|
| Primary agent coordinating sub-agents | `SwarmEngine` decomposes prompts into parallel phases via Gemini |
| Store/retrieve structured data from a database | Supabase: `threads`, `agent_traces`, `context_items`, `memories` (pgvector) |
| Multiple MCP tools | Tavily, Wikipedia, Google Calendar, Notion, Gmail, OpenWeatherMap, Python Executor |
| Multi-step workflows | Phase-based `asyncio.gather` execution; each phase result written to shared Blackboard |
| API-based deployment | FastAPI + SSE; Docker + Cloud Run `cloudbuild.yaml` included |

---

## Project Structure

```
nexus-hackathon/
├── nexus/                  # Python package (FastAPI backend)
│   ├── agents/             # All specialist agents + orchestrator
│   ├── memory/             # Supabase client + vector store
│   ├── mcp_servers/        # MCP tool wrappers
│   ├── models/schemas.py   # Pydantic models + agent registry
│   ├── observability/      # SSE trace system
│   ├── routes/             # FastAPI routers (chat, memory, system)
│   ├── config.py           # Centralised env config
│   └── main.py             # FastAPI app + lifespan
├── frontend/               # Vanilla JS + D3 + Tailwind
│   ├── index.html          # Scroll-story landing page
│   ├── studio.html         # Mission Control (live D3 swarm graph)
│   ├── memory.html         # Memory vault + Supabase traces
│   └── nexus-core.js       # Shared SSE client + Supabase init
├── run.sh                  # Start server (repo root)
└── setup.sh                # First-time setup
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/chat` | SSE swarm execution stream |
| `POST` | `/plan` | Generate phase plan without executing |
| `GET` | `/health` | System health + agent count |
| `GET` | `/agents` | All registered agent identities |
| `GET` | `/agents/{name}` | Single agent info |
| `GET` | `/memory/{user_id}` | All 4 memory layers |
| `GET` | `/memory-graph/{user_id}` | D3-compatible knowledge graph |
| `GET` | `/memory-search?query=` | Semantic vector search |
| `GET` | `/trace/{session_id}` | Full trace for a session |
| `GET` | `/docs` | Interactive Swagger UI |

---

## Technology Stack

- **Backend**: Python 3.11, FastAPI, Pydantic v2, aiohttp, asyncio
- **LLM**: Gemini 2.0 Flash (planning, response generation, embeddings)
- **Database**: Supabase (PostgreSQL + pgvector for semantic search)
- **Frontend**: Vanilla JS, D3.js v7, Tailwind CSS, Server-Sent Events
- **Deployment**: Docker, Google Cloud Run, Cloud Build
