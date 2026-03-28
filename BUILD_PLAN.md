# NEXUS — Master Build Plan

> Work through this top to bottom. Each phase has a clear "done when" test.
> Never move to the next phase until the current one passes its test.
> DEMO_MODE=true by default — everything runs without real API keys until Phase 4.

---

## Current State
```
nexus-hackathon/
├── NEXUS_OVERVIEW.md        ✅ done
├── NEXUS_Project_Documentation.docx  ✅ done
├── BUILD_PLAN.md            ✅ this file
├── frontend/
│   └── assets/agents/       ← agent images go here (upload + crop script)
└── nexus/
    ├── agents/              ← empty
    ├── fixtures/            ← empty
    ├── mcp_servers/         ← empty
    ├── memory/              ← empty
    ├── models/              ← empty
    ├── observability/       ← empty
    ├── workflows/           ← empty
    └── venv/                ✅ created
```

---

## Phase 0 — Agent Images (do this first, unblocks frontend)

**Goal:** 10 individual agent PNG files cropped from the master illustration.

**Steps:**
1. Upload the master agent illustration image into this chat
2. Claude writes a Python crop script and runs it
3. 10 files land in `frontend/assets/agents/`

**Files produced:**
```
frontend/assets/agents/
  nexus_core.png   atlas.png    lumen.png    dash.png     forge.png
  sage.png         chrono.png   mnemo.png    flux.png     quest.png
```

**Done when:** All 10 PNG files exist in the folder and look correct.

---

## Phase 1 — Data Contracts (30 min)

**Goal:** Define every data shape used across the entire project.
Both backend and frontend build against these models — nothing else can start without them.

**Files to write:**
```
nexus/models/__init__.py
nexus/models/schemas.py
```

**What schemas.py defines:**
- `ChatRequest`         — what the frontend sends to /chat
- `AgentResult`         — what every agent returns (summary, steps, tool_calls, memory_writes)
- `TraceEvent`          — what the SSE stream emits per agent step
- `WorkflowStatus`      — current step, % complete, status
- `MCPCardDetail`       — full detail for MCP card click (steps, data written, conflicts)
- `MemoryEntry`         — a Firestore memory record
- `Task`                — a task object
- `SuggestionChip`      — a proactive follow-up suggestion

**Done when:**
```bash
cd nexus && source venv/bin/activate
python3 -c "from models.schemas import ChatRequest, TraceEvent, AgentResult; print('schemas OK')"
```
Prints: `schemas OK`

---

## Phase 2 — Observability (30 min)

**Goal:** The AgentTracer — the system that makes the UI come alive.
Every agent call goes through this. It emits SSE events the frontend consumes.

**Files to write:**
```
nexus/observability/__init__.py
nexus/observability/agent_tracer.py
```

**What agent_tracer.py does:**
- Maintains a per-request event queue
- `tracer.emit(agent, tool, action, status, detail)` — adds event to queue
- `tracer.stream()` — async generator that yields SSE-formatted strings
- `tracer.get_trace()` — returns full trace for MCP card detail view

**Done when:**
```bash
python3 -c "
from observability.agent_tracer import AgentTracer
t = AgentTracer('test-session')
t.emit('Atlas', 'tavily_search', 'Searching...', 'running')
t.emit('Atlas', 'tavily_search', 'Found 5 results', 'done', {'count': 5})
print(t.get_trace())
print('tracer OK')
"
```
Prints the trace dict and `tracer OK`

---

## Phase 3 — FastAPI Shell (45 min)

**Goal:** A running server with all endpoints defined, returning mock data.
The frontend can connect to this immediately.

**Files to write:**
```
nexus/main.py
nexus/.env
nexus/.gitignore
```

**Endpoints in main.py:**
```
POST /chat              — receives prompt, returns SSE stream of TraceEvents + final response
GET  /trace/{id}        — returns full trace for a completed request
GET  /mcp-detail/{id}/{tool}  — returns MCPCardDetail for a specific tool call
GET  /memory/{user_id}  — returns all 4 memory layers for a user
GET  /agents            — returns list of all 9 agents with status
GET  /health            — health check
```

**Done when:**
```bash
cd nexus && source venv/bin/activate && uvicorn main:app --reload --port 8000
```
Then open http://localhost:8000/health → returns `{"status": "ok", "mode": "demo"}`
And http://localhost:8000/agents → returns list of 9 agents

---

## Phase 4 — Memory Layer (45 min)

**Goal:** Mnemo's 4-layer memory system backed by Firestore (or in-memory dict for DEMO_MODE).

**Files to write:**
```
nexus/memory/__init__.py
nexus/memory/session_cache.py     ← Layer 1: in-memory session.state
nexus/memory/firestore_client.py  ← Layers 2, 3, 4: Firestore operations
nexus/memory/vector_store.py      ← Layer 4: semantic search (stub in DEMO_MODE)
```

**DEMO_MODE behavior:**
- `firestore_client.py` uses a local Python dict instead of real Firestore
- `vector_store.py` does simple keyword matching instead of real vector search
- Everything still works and produces realistic output

**Done when:**
```bash
python3 -c "
from memory.session_cache import SessionCache
from memory.firestore_client import FirestoreClient
s = SessionCache('session-1')
s.set('atlas_result', {'topics': ['OOP', 'async', 'decorators']})
print(s.get('atlas_result'))
f = FirestoreClient(demo_mode=True)
f.write_daily_log('user-1', 'Ran exam prep workflow')
print(f.get_daily_log('user-1'))
print('memory OK')
"
```
Prints the data and `memory OK`

---

## Phase 5 — MCP Servers (2 hours)

**Goal:** All 12 MCP tool servers — each returns real data or realistic fixtures.

**Files to write:**
```
nexus/mcp_servers/__init__.py
nexus/mcp_servers/search_mcp.py       ← Tavily + Brave (fallback: DuckDuckGo scrape)
nexus/mcp_servers/scraper_mcp.py      ← BeautifulSoup web scraper (free, no key)
nexus/mcp_servers/wikipedia_mcp.py    ← Wikipedia REST API (free, no key)
nexus/mcp_servers/youtube_mcp.py      ← youtube-transcript-api (free, no key)
nexus/mcp_servers/weather_mcp.py      ← OpenWeatherMap (free key) or wttr.in (no key)
nexus/mcp_servers/calendar_mcp.py     ← Google Calendar or fixture
nexus/mcp_servers/gmail_mcp.py        ← Gmail or fixture
nexus/mcp_servers/maps_mcp.py         ← Google Maps or fixture
nexus/mcp_servers/filesystem_mcp.py   ← Local file read/write
nexus/mcp_servers/executor_mcp.py     ← Sandboxed Python exec()
nexus/mcp_servers/firestore_mcp.py    ← Firestore CRUD via firebase-admin
nexus/mcp_servers/notion_mcp.py       ← Notion API or Firestore fallback
```

**Free-tier fallback strategy (zero keys needed for demo):**
| MCP | Real API | Free fallback (no key) |
|-----|----------|------------------------|
| Search | Tavily / Brave | DuckDuckGo HTML scrape |
| Scraper | Firecrawl | BeautifulSoup + requests |
| Weather | OpenWeatherMap | wttr.in (completely free, no key) |
| Calendar | Google Calendar | JSON fixture |
| Gmail | Gmail API | JSON fixture |
| Maps | Google Maps | JSON fixture |
| Notion | Notion API | Firestore |

**Done when:**
```bash
python3 -c "
from mcp_servers.search_mcp import SearchMCP
from mcp_servers.weather_mcp import WeatherMCP
from mcp_servers.wikipedia_mcp import WikipediaMCP
import asyncio
async def test():
    wiki = WikipediaMCP()
    result = await wiki.search('Python programming language')
    print('Wikipedia:', result['title'])
    weather = WeatherMCP()
    w = await weather.get_current('Mumbai')
    print('Weather:', w['description'])
    print('mcp_servers OK')
asyncio.run(test())
"
```

---

## Phase 6 — Core Agents (2 hours)

**Goal:** The 5 real agents — each with a distinct personality, owned tools, and structured output.

**Files to write:**
```
nexus/agents/__init__.py
nexus/agents/orchestrator.py   ← NEXUS Core — intent router, AgentTool wrappers
nexus/agents/atlas.py          ← Research — Tavily, Brave, Wikipedia, YouTube, Scraper
nexus/agents/chrono.py         ← Scheduler — Calendar, Maps, Weather
nexus/agents/sage.py           ← Notes — Filesystem, Notion/Firestore, Drive
nexus/agents/mnemo.py          ← Memory — all 4 Firestore layers
nexus/agents/flux.py           ← Briefing — Weather, Gmail, suggestions
```

**Stub agents (structured mock responses, still animate the UI):**
```
nexus/agents/dash.py           ← Tasks — stub
nexus/agents/quest.py          ← Goals — stub
nexus/agents/lumen.py          ← Analytics — stub
nexus/agents/forge.py          ← Workflow engine — stub
```

**Key ADK patterns every agent must follow:**
1. Wrapped as `AgentTool(agent=X)` on the orchestrator — never called directly
2. Returns `AgentResult` Pydantic model — never free-form text
3. Writes to namespaced `session.state["agentname_output"]` — never shared keys
4. System prompt defines personality + output format + which tools to use when
5. Uses `output_key="agentname_output"` in SequentialAgent pipelines

**Done when:**
```bash
python3 -c "
import asyncio, os
os.environ['DEMO_MODE'] = 'true'
from agents.orchestrator import create_orchestrator
async def test():
    orch = create_orchestrator()
    result = await orch.run('What is machine learning?')
    print('Agent:', result.agent_name)
    print('Summary:', result.summary[:100])
    print('agents OK')
asyncio.run(test())
"
```

---

## Phase 7 — Workflows (1.5 hours)

**Goal:** 3 multi-step workflows using all 3 ADK primitives.

**Files to write:**
```
nexus/workflows/__init__.py
nexus/workflows/exam_prep.py      ← SequentialAgent + ParallelAgent
nexus/workflows/day_planner.py    ← ParallelAgent + SequentialAgent
nexus/workflows/research_loop.py  ← LoopAgent (MCP calls outside the loop)
```

**Critical ADK rules for workflows:**
- LoopAgent NEVER contains MCP calls — only pure Gemini reasoning
- ParallelAgent sub-agents MUST write to unique session.state keys
- SequentialAgent steps MUST use {key?} template injection between steps
- Every step emits a TraceEvent via AgentTracer before and after

**Workflow: exam_prep**
```
SequentialAgent:
  Step 1: Atlas   → scrape + research  → output_key: "exam_topics"
  Step 2: Sage    → structure notes    → reads {exam_topics?}  → output_key: "exam_notes"
  Step 3: ParallelAgent:
            Chrono → block slots       → output_key: "chrono_output"
            Dash   → create checklist  → output_key: "dash_output"
  Step 4: Mnemo   → save to memory     → reads all outputs
```

**Workflow: day_planner**
```
ParallelAgent (Step 1):
  Dash   → pending tasks   → output_key: "pending_tasks"
  Chrono → calendar        → output_key: "todays_calendar"
  Flux   → weather         → output_key: "weather_data"
SequentialAgent (Steps 2-4):
  Step 2: Flux   → synthesise  → reads all 3 outputs → output_key: "briefing_plan"
  Step 3: Chrono → time-blocks → reads {briefing_plan?}
  Step 4: Mnemo  → save prefs
```

**Workflow: research_loop**
```
SequentialAgent (MCP calls BEFORE loop):
  Step 1: Atlas → search Tavily + Wikipedia → output_key: "raw_research"
  Step 2: LoopAgent (pure Gemini, no MCP):
            Reviewer scores quality 1-10
            If < 7 AND iterations < 3: loop
            If ≥ 7 OR max reached: escalate=True
  Step 3: Sage → structure notes → save to Firestore
  Step 4: Mnemo → save topic interest
```

**Done when:**
```bash
python3 -c "
import asyncio, os
os.environ['DEMO_MODE'] = 'true'
from workflows.exam_prep import run_exam_prep
async def test():
    result = await run_exam_prep('Python OOP exam tomorrow', 'user-1', 'session-1')
    print('Steps completed:', len(result.steps))
    print('Agents used:', [s.agent for s in result.steps])
    print('workflows OK')
asyncio.run(test())
"
```

---

## Phase 8 — Demo Fixtures (30 min)

**Goal:** Realistic cached responses for every MCP tool. DEMO_MODE=true uses these.
This is your insurance policy — if any live API fails, the demo never breaks.

**Files to write:**
```
nexus/fixtures/search_results.json      ← Tavily/Brave search results
nexus/fixtures/calendar_events.json     ← Google Calendar events
nexus/fixtures/weather.json             ← OpenWeatherMap weather data
nexus/fixtures/tasks.json               ← User's pending tasks
nexus/fixtures/gmail_inbox.json         ← Email summaries
nexus/fixtures/maps_directions.json     ← Directions + travel time
nexus/fixtures/wikipedia_results.json   ← Wikipedia article summaries
nexus/fixtures/youtube_transcript.json  ← Sample transcript
nexus/fixtures/user_profile.json        ← User preferences + history
```

**Done when:** Every MCP server runs cleanly with DEMO_MODE=true and returns fixture data.

---

## Phase 9 — Frontend: Landing + Agent Roster (2 hours)

**Goal:** The first thing judges see. Google-native, clean, impressive.

**Files to write:**
```
frontend/index.html     ← landing page + agent roster
frontend/styles.css     ← full Google design system
frontend/agents.js      ← roster scroll, agent detail expand, intro animations
```

**Landing page sections:**
1. Top bar — NEXUS logo + "Powered by Google ADK · Gemini · MCP"
2. Hero — headline + subheadline + "Meet the team" CTA + "Start session" button
3. Main agent reveal — NEXUS Core large avatar + info on right
4. Agent roster — horizontally scrollable row of 9 agent cards
5. Each card: image left, name + role + traits + MCPs right, unique color accent
6. Click agent → full capability breakdown expands
7. "Start session" → transitions to app.html

**Done when:** Open frontend/index.html in browser.
- Loads without errors
- Agent roster scrolls horizontally showing 2.5 cards
- Clicking an agent expands their detail panel
- "Start session" button is visible and styled

---

## Phase 10 — Frontend: Session UI (2 hours)

**Goal:** The mission control. The thing that wins the hackathon.

**Files to write:**
```
frontend/app.html       ← 3-panel session UI
frontend/app.js         ← SSE consumer, agent graph, MCP cards, response streaming
```

**Left rail behavior:**
- Starts empty
- When SSE event with status="running" arrives: card flies in from left with swoosh
- Card shows: agent color dot + agent name + tool name + action text (updates live)
- When status="done": card snaps to compact done state with checkmark
- Clicking done card → opens MCPCardDetail drawer

**Center panel behavior:**
- Agent coordination graph: 9 nodes pre-rendered as SVG, edges between them
- Nodes pulse with agent's color when that agent is active
- Response area: text streams word by word with agent attribution tags
- [Atlas] tag in blue before Atlas's contribution
- [Chrono] tag in red before Chrono's contribution
- 3 suggestion chips appear below response when workflow completes

**Right rail behavior:**
- 9 agent cards always visible
- Idle: dim, "Ready" status
- Active: glows in agent color, thinking dots animate below name
- Done: returns to normal, green checkmark briefly

**Done when:**
Open frontend/app.html with backend running on :8000
Type "prepare for my exam tomorrow"
- See MCP cards fly into left rail one by one
- See agent graph nodes pulse
- See response stream with attribution tags
- See Mnemo card glow purple at end
- See 3 suggestion chips appear

---

## Phase 11 — Wire Everything Together (1 hour)

**Goal:** Frontend talks to real backend. End-to-end flow works live.

**Tasks:**
- Update main.py /chat endpoint to call real orchestrator (not mock)
- Verify SSE events match what frontend expects
- Test all 3 workflows from the UI
- Verify MCP card detail drawer shows real data from AgentTracer
- Verify Mnemo memory panel shows real Firestore data
- Test DEMO_MODE=true fallback still works

**Done when:**
Both these work:
1. `DEMO_MODE=true` — everything runs with fixtures, zero API keys
2. `DEMO_MODE=false` — everything runs with real APIs (after keys are set up)

---

## Phase 12 — Polish (1 hour)

**Goal:** Remove anything broken, make everything that's shown look perfect.

**Checklist:**
- [ ] All 9 agent images display correctly
- [ ] Agent colors consistent across graph, cards, rail, response tags
- [ ] MCP card fly-in animation smooth (no jank)
- [ ] Response streaming feels natural (not too fast, not too slow)
- [ ] Mnemo memory panel renders correctly
- [ ] MCP card detail drawer opens/closes cleanly
- [ ] Mobile view doesn't break (basic responsive)
- [ ] No console errors in browser
- [ ] Backend logs are clean (no Python warnings)
- [ ] All 3 demo workflows run without errors
- [ ] DEMO_MODE fixtures give realistic, impressive output

---

## Phase 13 — Deploy to Cloud Run (1 hour)

**Goal:** Public URL that judges can access from anywhere.

**Steps:**
1. Set up GCP project + enable APIs (see NEXUS_OVERVIEW.md Step 1-2)
2. `gcloud auth login`
3. Store all API keys in GCP Secret Manager
4. Write `nexus/Dockerfile`
5. Write `nexus/cloudbuild.yaml`
6. `gcloud builds submit --config cloudbuild.yaml`
7. Get public Cloud Run URL

**Done when:**
`https://nexus-XXXXX.run.app/health` returns `{"status": "ok"}`
Full demo works on the public URL.

---

## Phase 14 — Demo Video (30 min)

**Goal:** 3-minute screen recording covering all 5 demos.

**Script:**
- 0:00–0:30 — Landing page + agent roster scroll + click one agent for detail
- 0:30–1:00 — Click "Start session", watch agents wake up one by one
- 1:00–2:30 — Type "Prepare for my Python interview tomorrow"
              Watch MCP cards fly in, graph pulse, response stream
              Click a completed MCP card → show full detail
- 2:30–3:00 — Type "I'm behind and stressed"
              Watch Flux respond + Mnemo save + chips appear

**Tools:** QuickTime (Mac) → File → New Screen Recording. Free, built-in.

---

## Quick Reference — Key Rules While Coding

```python
# RULE 1: AgentTool not sub_agents
# WRONG:
root_agent = LlmAgent(sub_agents=[atlas, chrono])
# RIGHT:
root_agent = LlmAgent(tools=[AgentTool(atlas), AgentTool(chrono)])

# RULE 2: Namespaced session.state keys
# WRONG:
output_key = "result"       # two agents both write "result" → race condition
# RIGHT:
output_key = "atlas_output" # unique per agent

# RULE 3: MCP calls OUTSIDE LoopAgent
# WRONG:
loop = LoopAgent(agents=[atlas_with_mcp_tools, reviewer])  # times out
# RIGHT:
seq = SequentialAgent(agents=[
    atlas_with_mcp_tools,   # MCP calls here, BEFORE the loop
    LoopAgent(agents=[reviewer_gemini_only])  # pure Gemini reasoning only
])

# RULE 4: Template injection between sequential steps
# WRONG:
step2 = LlmAgent(instruction="Now structure the notes.")  # doesn't get step1 output
# RIGHT:
step2 = LlmAgent(instruction="Here are the research results: {atlas_output?}\nNow structure these into notes.")

# RULE 5: Structured output always
# WRONG:
return "I found 14 topics: OOP, async..."  # can't populate MCP card detail
# RIGHT:
return AgentResult(summary="Found 14 topics", steps=[...], tool_calls=[...], memory_writes=[...])
```

---

## API Keys Needed (add to .env as you go)

```bash
# Phase 3 (main.py) — only this needed to start
DEMO_MODE=true
GOOGLE_API_KEY=                    # aistudio.google.com — free, no card

# Phase 5 (MCP servers) — add as you build each server
TAVILY_API_KEY=                    # tavily.com — free, no card
BRAVE_API_KEY=                     # brave.com/search/api — free, no card
OPENWEATHER_API_KEY=               # openweathermap.org — free, no card
FIRECRAWL_API_KEY=                 # firecrawl.dev — free, no card
NOTION_TOKEN=                      # notion.so/my-integrations — free

# Phase 13 (deployment) — only needed for Cloud Run
GOOGLE_CLOUD_PROJECT=nexus-hackathon
GOOGLE_APPLICATION_CREDENTIALS=./nexus-service-account.json
```

---

## Status Tracker

Mark each phase as you complete it:

- [ ] Phase 0  — Agent images cropped
- [x] Phase 1  — schemas.py
- [x] Phase 2  — agent_tracer.py
- [x] Phase 3  — main.py (FastAPI shell)
- [x] Phase 4  — Memory layer
- [x] Phase 5  — MCP servers
- [x] Phase 6  — Core agents (Demo mode complete, Live agents stubbed)
- [x] Phase 7  — Workflows
- [x] Phase 8  — Demo fixtures
- [x] Phase 9  — Frontend: landing + roster
- [x] Phase 10 — Frontend: session UI
- [x] Phase 11 — Wire everything together
- [x] Phase 12 — Polish
- [x] Phase 13 — Deploy to Cloud Run (Dockerfile + cloudbuild.yaml created)
- [ ] Phase 14 — Demo video

---

*Start with Phase 0 (agent images) and Phase 1 (schemas.py) in parallel.*
*Phase 0 unblocks the frontend. Phase 1 unblocks everything else.*
