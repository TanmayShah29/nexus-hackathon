# NEXUS — Intelligent Multi-Agent Productivity OS

> **Google Cloud Gen AI Academy — APAC Edition (Hack2Skill 2025)**
> Built on Google ADK · Gemini 1.5 Flash · MCP · Firestore · Cloud Run · FastAPI

---

## What We Are Building

NEXUS is a **multi-agent AI productivity system** where a team of 9 specialist AI agents
collaborate in real time to manage a user's entire cognitive workload — tasks, schedules,
notes, research, goals, memory, and analytics — from a single natural language prompt.

Unlike generic AI chatbots that respond to one prompt at a time, NEXUS deploys a
**coordinated team of experts**. When you say "prepare for my exam tomorrow", five agents
activate simultaneously: one researches the syllabus, one structures notes, one blocks
calendar time, one creates a task checklist, and one silently saves everything to memory.

The user sees every single step happening in real time through a transparent,
Google-native mission control UI.

---

## The Problem We Solve

Knowledge workers today face a **fragmentation crisis**:
- Tasks live in one app, calendar in another, notes in a third
- Research takes hours instead of minutes
- Context is lost between work sessions
- Switching between 9+ tools per day kills productivity

**NEXUS solves all of this from one interface, with one prompt.**

---

## The 9 Agents

Each agent has a name, illustrated personality, unique color, and owned set of tools.
They never talk to each other directly — all coordination happens through the
NEXUS orchestrator via ADK's AgentTool pattern.

| Agent     | Name      | Role                              | Color           | Personality         |
|-----------|-----------|-----------------------------------|-----------------|---------------------|
| Orchestrator | NEXUS Core | Routes intent, coordinates all   | Google Blue     | Silent coordinator  |
| Research  | Atlas     | Web search, summarization, citations | #1a73e8 Blue | Curious scholar     |
| Analytics | Lumen     | Productivity reports, patterns    | #0f9d58 Green   | Blunt analyst       |
| Tasks     | Dash      | Task CRUD, priorities, execution  | #fbbc04 Yellow  | No-nonsense executor|
| Workflow  | Forge     | Multi-step pipeline orchestration | #c2185b Pink    | Systematic builder  |
| Notes     | Sage      | Store, search, retrieve knowledge | #34a853 Green   | Quiet librarian     |
| Scheduler | Chrono    | Calendar, time-blocking, conflicts| #ea4335 Red     | Efficient timekeeper|
| Memory    | Mnemo     | 4-layer persistent memory system  | #9334e6 Purple  | Silent watcher      |
| Briefing  | Flux      | Context synthesis, suggestions    | #00bcd4 Cyan    | Empathetic peer     |
| Goals     | Quest     | Goal decomposition, roadmaps      | #ff6d00 Orange  | Goal strategist     |

---

## Tech Stack

### Core AI & Agents

| Technology             | Purpose                                                                 |
|------------------------|-------------------------------------------------------------------------|
| **Google ADK**         | Agent framework — native Gemini integration, workflow primitives        |
| **Gemini 1.5 Flash**   | LLM powering all agents — free tier, fast, excellent reasoning          |
| **ADK LlmAgent**       | Each specialist agent — Gemini-powered reasoning with tools             |
| **ADK SequentialAgent**| Ordered pipelines — step-by-step workflows                              |
| **ADK ParallelAgent**  | Concurrent execution — fetch tasks + calendar + weather simultaneously  |
| **ADK LoopAgent**      | Iterative refinement — research loop, scores quality, retries if needed |
| **ADK AgentTool**      | Sub-agent wrapping — root agent calls specialists as functions          |

### Backend

| Technology        | Purpose                                              |
|-------------------|------------------------------------------------------|
| **FastAPI**        | REST API + Server-Sent Events (SSE) for live trace  |
| **Uvicorn**        | ASGI server                                          |
| **Pydantic v2**    | Request/response validation + structured agent output|
| **Python 3.11+**   | Runtime                                              |
| **python-dotenv**  | Environment variable management                      |
| **httpx / aiohttp**| Async HTTP for MCP tool calls                        |
| **structlog**      | Structured logging                                   |

### Database & Memory

| Technology                  | Purpose                                              |
|-----------------------------|------------------------------------------------------|
| **Firestore**                | Primary database — tasks, notes, sessions, profiles  |
| **Firestore Vector Search**  | Semantic note search — recall by meaning             |
| **ADK session.state**        | Working memory — shared context within a workflow    |
| **firebase-admin SDK**       | Firestore Python client                              |

### MCP Tool Servers (14 total)

**Tier 1 — Directly coded (individually visible in agent trace):**

| MCP Server          | Agent Owner | Free Alternative Used          |
|---------------------|-------------|-------------------------------|
| Google Calendar     | Chrono      | Demo Google account            |
| Gmail               | Flux        | Demo Google account            |
| Google Drive        | Sage        | Demo Google account            |
| Google Maps         | Chrono      | Free tier ($200 credit)        |
| Tavily Search       | Atlas       | Free tier (1,000/mo)           |
| Brave Search        | Atlas       | Free tier (2,000/mo)           |
| Firecrawl           | Atlas       | BeautifulSoup fallback         |
| OpenWeatherMap      | Flux        | Free tier (1,000/day)          |
| Notion              | Sage        | Firestore fallback             |
| YouTube Transcript  | Atlas       | Open library — no key needed   |
| Wikipedia           | Atlas       | Open REST API — no key needed  |
| Filesystem          | Sage        | Local sandbox                  |
| Python Executor     | Lumen       | Sandboxed exec()               |
| Firestore MCP       | Mnemo       | firebase-admin                 |

**Tier 2 — Composio gateway (mentioned in README, not called live in demo):**
Slack, GitHub, Linear, Jira, Todoist, Trello, Discord, Telegram, HubSpot, Airtable,
Microsoft 365, Figma, and 488 more apps via one API key.

### Frontend

| Technology           | Purpose                                              |
|----------------------|------------------------------------------------------|
| **Vanilla HTML/CSS/JS**| No framework overhead — fastest to build           |
| **Google Sans + Roboto**| Google's own fonts — feels native to judges       |
| **JetBrains Mono**   | Trace log display                                    |
| **CSS animations**   | Agent graph, MCP card fly-in, response streaming     |
| **EventSource API**  | Consumes SSE stream from FastAPI                     |
| **8px grid system**  | Google Material Design spacing                       |

### Deployment

| Technology              | Purpose                       |
|-------------------------|-------------------------------|
| **Google Cloud Run**     | Serverless container hosting  |
| **Cloud Build**          | CI/CD pipeline                |
| **GCP Secret Manager**   | API keys in production        |
| **Docker**               | Container packaging           |

---

## Architecture — How It Works

```
User types a prompt
        │
        ▼
FastAPI /chat endpoint
        │
        ▼
AgentTracer wraps the call ──► starts emitting SSE events to frontend
        │
        ▼
NEXUS Orchestrator (LlmAgent + Gemini 1.5 Flash)
  ├─ Classifies intent
  ├─ Selects which agents / workflow to activate
  └─ Calls sub-agents via AgentTool (retains full context throughout)
        │
        ├──► SequentialAgent (ordered pipeline)
        │     Step 1 ─► Atlas  (research)    writes → session.state["atlas_result"]
        │     Step 2 ─► Sage   (notes)       reads  ← {atlas_result?}
        │     Step 3 ─► ParallelAgent
        │                 ├─ Chrono  (schedule)   writes → session.state["chrono_output"]
        │                 └─ Dash    (tasks)       writes → session.state["dash_output"]
        │     Step 4 ─► Mnemo  (memory)      saves everything to Firestore
        │
        ├──► LoopAgent (research refinement — max 3 iterations)
        │     Atlas searches (MCP calls happen BEFORE the loop — avoids ADK timeout bug)
        │     Reviewer scores quality (1-10)
        │     Loop exits when score ≥ 7 or max iterations reached
        │
        └──► Single agent call (simple requests)
              e.g. "what are my tasks today?" ─► Dash only
        │
        ▼
AgentTracer emits structured SSE events in real time:
  { "agent": "Atlas",  "tool": "tavily_search", "status": "running", "action": "Searching for Python topics..." }
  { "agent": "Atlas",  "tool": "tavily_search", "status": "done",    "action": "Found 14 topics", "detail": {...} }
  { "agent": "Chrono", "tool": "calendar",      "status": "running", "action": "Checking free slots..." }
        │
        ▼
Frontend receives SSE stream and updates UI simultaneously:
  LEFT RAIL   ─► MCP cards fly in from left as each tool fires
  CENTER      ─► Agent graph nodes pulse, response streams word-by-word
  RIGHT RAIL  ─► Agent faces glow in their color while working
        │
        ▼
Workflow completes:
  ─► MCP cards snap-shrink to compact done state
  ─► Mnemo card glows purple briefly: "Memory saved"
  ─► Flux generates 3 proactive suggestion chips below response
```

---

## The 4-Layer Memory System (Mnemo)

```
Layer 1 — Working memory     ADK session.state              Current workflow only
Layer 2 — Daily log          Firestore memory/{userId}/{date} Today's events, 30-day retention
Layer 3 — Long-term profile  Firestore users/{userId}/profile Preferences, habits, permanent
Layer 4 — Semantic search    Firestore Vector Search          Recall notes by meaning, not keywords
```

After every interaction, Mnemo scores its importance (1–5).
Only interactions scoring ≥ 3 are written to Layer 3 (long-term profile).
All interactions are written to Layer 2 (daily log).

---

## Multi-Step Workflow Examples

### "Prepare for my exam tomorrow"
```
1. Atlas    → Firecrawl / BeautifulSoup scrapes syllabus → session.state["topics"]
2. Atlas    → Tavily searches each topic                 → session.state["research"]
3. Sage     → Structures notes → saves to Firestore
4. PARALLEL → Chrono blocks 3 study slots on Calendar
             → Dash creates revision checklist in tasks
5. Mnemo    → Saves "user has exam, prefers morning study" to profile
6. Flux     → Generates 3 follow-up suggestion chips
```

### "Plan my day"
```
1. PARALLEL → Dash fetches pending tasks
             → Chrono reads today's calendar
             → Flux checks OpenWeatherMap
2. Flux     → Synthesises context, detects conflicts
3. Chrono   → Creates time-blocks, resolves conflicts
4. Mnemo    → Updates productivity preferences
5. Flux     → Delivers structured briefing card in UI
```

### "Research quantum computing and make me notes"
```
1. Atlas    → Tavily + Brave + Wikipedia search (BEFORE LoopAgent)
2. LOOP     → Reviewer scores quality (1-10)
             → If < 7: Atlas searches more, loops again (max 3×)
             → If ≥ 7: exits loop
3. Sage     → Structures research into Firestore / Notion pages
4. Mnemo    → Saves topic interest to long-term profile
```

---

## UI Layout

```
┌──────────────────┬────────────────────────────────┬──────────────────┐
│   LEFT RAIL      │         CENTER PANEL            │   RIGHT RAIL     │
│                  │                                 │                  │
│  MCP Activity    │  Agent coordination graph       │  Agent roster    │
│                  │  (9 nodes, edges pulse when     │                  │
│  Cards fly in    │   data flows between agents)    │  9 agent cards   │
│  from left edge  │                                 │  each with       │
│  as each tool    │  ─────────────────────────────  │  illustrated     │
│  fires           │                                 │  face + name     │
│                  │  Response streams word by word  │  + status        │
│  Done cards      │  with agent attribution tags    │                  │
│  snap-shrink     │  e.g. [Atlas] Found 14 topics   │  Mnemo always    │
│  and stack       │       [Chrono] Blocked 3 slots  │  present,        │
│                  │                                 │  always watching │
│  Click any card  │  ─────────────────────────────  │                  │
│  → full detail   │  ┌─────────────────────────┐   │  Active agents   │
│  of what that    │  │  Type your prompt...    │   │  glow in their   │
│  agent did       │  └─────────────────────────┘   │  unique color    │
└──────────────────┴────────────────────────────────┴──────────────────┘
```

---

## Known Issues & Solutions

| # | Issue                                              | Severity | Solution                                                     |
|---|----------------------------------------------------|----------|--------------------------------------------------------------|
| 1 | MCPToolset inside LoopAgent times out              | Critical | MCP calls happen before the loop in a prior SequentialAgent  |
| 2 | Built-in tools can't coexist with MCP tools        | Critical | One tool type per agent, each wrapped as AgentTool           |
| 3 | ParallelAgent race condition on session.state      | Critical | Strictly namespaced keys — session.state["agentname_output"] |
| 4 | OAuth2 for Calendar / Gmail breaks in Cloud Run    | Critical | Pre-generated tokens stored in GCP Secret Manager            |
| 5 | SequentialAgent output_key not auto-injected       | Medium   | Explicit {key?} template in each next step's instruction     |
| 6 | Pydantic validation error on MCPToolset            | Medium   | Use get_tools_async() + AsyncExitStack cleanup pattern       |
| 7 | Live APIs fail during demo                         | Medium   | DEMO_MODE=true returns JSON fixtures — full UI still works   |
| 8 | 9 agents is too many to fully build in time        | Medium   | 5 core agents real, 4 return structured stubs                |

---

## Demo Strategy

Five demos, ~10 minutes total, each hitting a different judging criterion:

| Demo              | Time  | Prompt                                       | Criterion hit               |
|-------------------|-------|----------------------------------------------|-----------------------------|
| 1 — Simple        | 30s   | "Add review PR to my tasks"                  | Database storage            |
| 2 — Workflow      | 90s   | "Prepare for my Python interview tomorrow"   | Multi-agent coordination    |
| 3 — Research      | 60s   | "Research quantum computing, make notes"     | LoopAgent + MCP chain       |
| 4 — Adaptive      | 30s   | "I'm behind and stressed"                    | UX + real-world usefulness  |
| 5 — Transparency  | 60s   | Click any MCP card from Demo 2               | Explainable AI innovation   |

**The line that wins the demo:**
> "NEXUS isn't an AI assistant. It's a coordination layer. Through MCP it speaks the
> language of every tool your users already use. And unlike every other AI system you've
> seen today, NEXUS shows you exactly why it made every single decision."

---

## Build Order (5-day sprint)

| Day | Focus                        | Done when                                                        |
|-----|------------------------------|------------------------------------------------------------------|
| 1   | schemas + main.py + tracer + orchestrator + Atlas | "Research X" returns a live SSE trace         |
| 2   | Chrono + Sage + Mnemo + Firestore + fixtures       | exam_prep workflow runs in DEMO_MODE          |
| 3   | Frontend: landing + roster + 3-panel UI            | Full UI flow works with mocked SSE data       |
| 4   | Wire frontend to backend + MCP servers + workflows | Live demo runs without DEMO_MODE              |
| 5   | Polish + Cloud Run deploy + demo video             | Public URL live, 3-minute video recorded      |

---

*NEXUS — Built for Google Cloud Gen AI Academy APAC 2025*
*Google ADK · Gemini 1.5 Flash · MCP · Firestore · Cloud Run*
