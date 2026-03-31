# NEXUS — Developer Guide

## Repository Structure

```
nexus-hackathon/
├── nexus/                         # Python package (FastAPI backend)
│   ├── __init__.py                # Makes nexus/ importable as a package
│   ├── main.py                    # FastAPI app + lifespan + routes
│   ├── config.py                  # Single source of truth for all env vars
│   │
│   ├── agents/                    # All specialist agents
│   │   ├── base.py                # BaseAgent(name, blackboard) — all agents inherit this
│   │   ├── blackboard.py          # Shared dot-notation KV store with asyncio lock
│   │   ├── orchestrator.py        # SwarmEngine — phase planning + parallel execution
│   │   ├── research.py            # Atlas — web search, Wikipedia, synthesis
│   │   ├── scheduler.py           # Chrono — calendar, scheduling, conflict detection
│   │   ├── notes.py               # Sage — Notion, knowledge architecture
│   │   ├── memory.py              # Mnemo — 4-layer semantic recall
│   │   ├── task_manager.py        # Tasks — task CRUD
│   │   ├── goal_strategist.py     # Goals — 90-day roadmapping
│   │   ├── briefing.py            # Briefing — daily context synthesis
│   │   ├── analytics_agent.py     # Analytics — productivity metrics
│   │   ├── workflow.py            # Workflow — pipeline verification
│   │   └── gemini_client.py       # Gemini API (plan, embed, classify, respond)
│   │
│   ├── memory/
│   │   ├── supabase_client.py     # Supabase L2/L3/L4 client (singleton)
│   │   └── vector_store.py        # VectorStore: cosine similarity + KnowledgeGraph
│   │
│   ├── mcp_servers/               # Tool wrappers (all have demo_mode fallbacks)
│   │   ├── search_mcp.py          # Tavily → Brave → DuckDuckGo
│   │   ├── calendar_mcp.py        # Google Calendar (fixture in demo)
│   │   ├── weather_mcp.py         # OpenWeatherMap → wttr.in fallback
│   │   ├── wikipedia_mcp.py       # Wikipedia REST API (no key needed)
│   │   ├── firestore_mcp.py       # In-memory CRUD (task/notes store)
│   │   ├── notion_mcp.py          # Notion API (fixture in demo)
│   │   ├── gmail_mcp.py           # Gmail (fixture in demo)
│   │   ├── scraper_mcp.py         # BeautifulSoup web scraper
│   │   ├── executor_mcp.py        # Sandboxed Python executor
│   │   ├── filesystem_mcp.py      # Local file read/write (path-traversal safe)
│   │   ├── youtube_mcp.py         # youtube-transcript-api
│   │   └── maps_mcp.py            # Google Maps (fixture in demo)
│   │
│   ├── models/schemas.py          # All Pydantic models + AGENT_IDENTITY_MAP + AGENT_REGISTRY
│   ├── observability/agent_tracer.py  # AgentTracer SSE system + TraceStore
│   ├── logic/booster.py           # Zero-latency local logic engine
│   ├── utils/security.py          # API key verification, rate limiting
│   ├── utils/retry.py             # Exponential backoff + circuit breaker
│   ├── routes/chat.py             # POST /chat (SSE), POST /plan
│   ├── routes/memory.py           # GET /memory/*, /memory-graph/*, /memory-search
│   ├── routes/system.py           # GET /health, /agents, /agents/{name}
│   ├── core/boot.py               # Optional centralised boot sequence
│   ├── storage/                   # Blackboard JSON disk cache (git-ignored)
│   ├── tests/                     # pytest unit tests
│   └── fixtures/                  # JSON fixture files for demo mode
│
├── frontend/
│   ├── nexus-core.js              # Shared client: SSE, Supabase, getHealth()
│   ├── index.html                 # Scroll-story landing page (D3 opal nodes)
│   ├── studio.html                # Mission Control (live D3 swarm graph + SSE)
│   ├── memory.html                # Memory Vault (Supabase traces + stats)
│   └── mcp.html                   # Tool Gallery
│
├── run.sh                         # Start server from repo root
├── setup.sh                       # First-time setup (venv + .env)
├── README.md                      # Hackathon submission overview
└── DEMO_GUIDE.md                  # Prompt scenarios for judges
```

---

## Key Design Decisions & Rationale

### Why Gemini 2.0 Flash for planning?
The LLM generates the agent phase plan dynamically based on the prompt and current Blackboard state. This means the system adapts to multi-step requests without hardcoded routing logic. Fallback is a sensible two-phase default plan.

### Why FastAPI + SSE instead of WebSockets?
SSE is unidirectional (server → client), simpler to implement correctly, and naturally suited to the streaming trace pattern. The client doesn't need to send mid-stream messages. WebSockets would add complexity with no benefit here.

### Why Supabase over Firestore?
Supabase provides pgvector out of the box, which is the foundation for L4 semantic search. It also gives us a free Postgres database for L2/L3 persistence, and a real-time subscription channel for the memory page's live trace feed. Firestore was the original choice but had no vector search.

### Why a Blackboard pattern?
The Blackboard lets agents communicate results without tight coupling. Atlas writes `research.latest`; Chrono reads it without knowing who wrote it. This mirrors real multi-agent architectures and makes adding new agents trivial.

### Why `lru_cache` on config functions?
Environment variables don't change during a process lifetime. Caching with `lru_cache` avoids repeated `os.getenv()` calls while keeping the "single source of truth" property. Tests can call `.cache_clear()` to override.

### Why `asyncio.gather` for phases?
Agents within a phase are independent — they only share the Blackboard, which is thread-safe (asyncio, not threads). Gathering them runs them in parallel without threads, which is appropriate for I/O-bound async agents.

---

## Adding a New Agent

1. Create `nexus/agents/my_agent.py`
2. Inherit from `BaseAgent(name="my_agent", blackboard=blackboard)`
3. Implement `async def think(self, prompt: str) -> AgentResult`
4. Add to `AGENT_IDENTITY_MAP` in `models/schemas.py`
5. Add to `AgentName` Literal type in `models/schemas.py`
6. Register in `orchestrator.py → _make_agent()` registry dict
7. Export from `agents/__init__.py`

## Adding a New MCP Tool

1. Create `nexus/mcp_servers/my_tool_mcp.py`
2. Implement the tool class with `demo_mode` constructor param and fixture fallback
3. Import from `nexus.config` (never raw `os.getenv`)
4. Add to `mcp_servers/__init__.py`
5. Use from any agent: `from nexus.mcp_servers.my_tool_mcp import MyToolMCP`
