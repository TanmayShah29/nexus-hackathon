"""
main.py — NEXUS FastAPI Server

All endpoints the frontend talks to.
Run with: uvicorn main:app --reload --port 8000

Endpoints:
    POST /chat                           → SSE stream of trace events + final response
    GET  /trace/{session_id}             → Full trace for a completed session
    GET  /mcp-detail/{session_id}/{tool} → MCP card detail for one tool call
    GET  /memory/{user_id}               → All 4 memory layers for a user
    GET  /agents                         → All 9 agents with live status
    GET  /agents/{name}                  → Single agent info
    GET  /health                         → Health check
    GET  /suggestions/{session_id}       → Proactive suggestion chips
"""

import os
import asyncio
import json
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

load_dotenv()

from models.schemas import (
    ChatRequest, AgentResult, SuggestionChip,
    HealthResponse, AgentsResponse, AgentInfo,
    UserMemory, MemoryEntry,
    AGENT_REGISTRY, AGENT_MAP,
)
from observability.agent_tracer import trace_store, AgentTracer, build_mcp_detail

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
VERSION   = "1.0.0"
PORT      = int(os.getenv("PORT", "8000"))


# ─────────────────────────────────────────────
# APP
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"\n{'='*52}")
    print(f"  NEXUS API — Multi-Agent Productivity OS")
    print(f"  Mode    : {'DEMO (fixtures)' if DEMO_MODE else 'LIVE (real APIs)'}")
    print(f"  Version : {VERSION}")
    print(f"  Agents  : {len(AGENT_REGISTRY)}")
    print(f"  Docs    : http://localhost:{PORT}/docs")
    print(f"{'='*52}\n")
    yield
    print("\nNEXUS API shutting down.")


app = FastAPI(
    title="NEXUS API",
    description="Intelligent Multi-Agent Productivity OS — Google Cloud Gen AI Academy APAC 2025",
    version=VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # Lock down to your domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# HEALTH
# ─────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health():
    return HealthResponse(
        status="ok",
        mode="demo" if DEMO_MODE else "live",
        version=VERSION,
        agents_loaded=len(AGENT_REGISTRY),
        mcp_servers_ready=12,
    )


# ─────────────────────────────────────────────
# AGENTS
# ─────────────────────────────────────────────

@app.get("/agents", response_model=AgentsResponse, tags=["agents"])
async def get_agents():
    """All 9 agents with their info and current status"""
    return AgentsResponse(agents=AGENT_REGISTRY, total=len(AGENT_REGISTRY))


@app.get("/agents/{agent_name}", response_model=AgentInfo, tags=["agents"])
async def get_agent(agent_name: str):
    agent = AGENT_MAP.get(agent_name)
    if not agent:
        raise HTTPException(404, f"Agent '{agent_name}' not found")
    return agent


# ─────────────────────────────────────────────
# CHAT — main SSE endpoint
# ─────────────────────────────────────────────

@app.post("/chat", tags=["chat"])
async def chat(request: ChatRequest):
    """
    Main endpoint. Returns a Server-Sent Events stream.

    The frontend opens this with fetch() + ReadableStream and receives:
      - {"type":"trace", ...}    — one per agent action (updates UI in real time)
      - {"type":"response", ...} — final AgentResult when workflow completes
      - {"type":"complete"}      — stream closed, connection ends

    All events are newline-delimited JSON prefixed with "data: "
    """
    tracer = trace_store.create(request.session_id)
    use_demo = request.demo_mode or DEMO_MODE

    async def event_generator() -> AsyncGenerator[str, None]:
        # Run the orchestrator concurrently — it pushes events into tracer queue
        # while we drain that queue and yield SSE chunks to the client.
        orchestrate_fn = _demo_orchestrate if use_demo else _live_orchestrate
        task = asyncio.create_task(orchestrate_fn(request, tracer))

        # Drain SSE events until tracer signals completion
        async for chunk in tracer.stream():
            yield chunk

        # Await result (should already be done by the time stream ends)
        try:
            result: AgentResult = await task
            yield f"data: {json.dumps({'type': 'response', 'result': result.model_dump()})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ─────────────────────────────────────────────
# TRACE
# ─────────────────────────────────────────────

@app.get("/trace/{session_id}", tags=["trace"])
async def get_trace(session_id: str):
    """Full trace for a completed session — all agent steps in order"""
    tracer = trace_store.get(session_id)
    if not tracer:
        raise HTTPException(404, f"Session '{session_id}' not found")
    return tracer.get_trace()


@app.get("/mcp-detail/{session_id}/{tool}", tags=["trace"])
async def get_mcp_detail(session_id: str, tool: str):
    """
    Full detail for one MCP tool call.
    Called when the user clicks a completed MCP card in the left rail.
    Returns MCPCardDetail: steps, state writes, memory writes, conflicts.
    """
    tracer = trace_store.get(session_id)
    if not tracer:
        raise HTTPException(404, f"Session '{session_id}' not found")
    detail = tracer.get_mcp_detail(tool)
    if not detail:
        raise HTTPException(404, f"No detail for tool '{tool}' in session '{session_id}'")
    return detail.model_dump()


# ─────────────────────────────────────────────
# MEMORY
# ─────────────────────────────────────────────

@app.get("/memory/{user_id}", response_model=UserMemory, tags=["memory"])
async def get_memory(user_id: str):
    """
    All 4 Mnemo memory layers for a user.
    Used by the memory panel in the UI.
    """
    if not DEMO_MODE:
        # TODO Phase 4: real Firestore client
        # from memory.firestore_client import FirestoreClient
        # return await FirestoreClient().get_all_memory(user_id)
        pass
    return _demo_memory(user_id)


# ─────────────────────────────────────────────
# SUGGESTIONS
# ─────────────────────────────────────────────

@app.get("/suggestions/{session_id}", tags=["chat"])
async def get_suggestions(session_id: str):
    """Proactive suggestion chips for a completed session"""
    tracer = trace_store.get(session_id)
    if not tracer:
        raise HTTPException(404, f"Session '{session_id}' not found")
    return {
        "session_id": session_id,
        "suggestions": [
            {"label": "Schedule revision time",   "prompt": "Block 2 hours for revision tomorrow",              "agent_hint": "chrono"},
            {"label": "Create practice questions", "prompt": "Generate 10 practice questions on these topics",   "agent_hint": "atlas"},
            {"label": "Set an exam reminder",      "prompt": "Remind me tonight at 9pm about tomorrow's exam",   "agent_hint": "chrono"},
        ],
    }


# ─────────────────────────────────────────────
# DEMO ORCHESTRATOR
# No API keys needed. All responses come from realistic inline fixtures.
# Intent is detected from the prompt and routed to the right demo workflow.
# ─────────────────────────────────────────────

async def _demo_orchestrate(request: ChatRequest, tracer: AgentTracer) -> AgentResult:
    prompt = request.prompt.lower()

    if any(w in prompt for w in ["exam", "study", "interview", "prepare", "test", "quiz", "revision"]):
        return await _demo_exam_prep(request, tracer)
    elif any(w in prompt for w in ["plan my day", "morning", "today's plan", "schedule today", "what's today"]):
        return await _demo_day_planner(request, tracer)
    elif any(w in prompt for w in ["research", "find out", "look up", "what is", "explain", "tell me about"]):
        return await _demo_research(request, tracer)
    elif any(w in prompt for w in ["task", "todo", "add", "remind me", "checklist", "to-do"]):
        return await _demo_add_task(request, tracer)
    elif any(w in prompt for w in ["stressed", "tired", "overwhelmed", "behind", "anxious", "exhausted"]):
        return await _demo_adaptive(request, tracer)
    else:
        return await _demo_general(request, tracer)


# ── Workflow: Exam Prep ─────────────────────────────────────

async def _demo_exam_prep(request: ChatRequest, tracer: AgentTracer) -> AgentResult:
    tracer.emit_workflow_start("exam_prep", 5)
    await asyncio.sleep(0.3)

    # Step 1 — Atlas scrapes + searches
    tracer.emit("atlas", "web_scraper", "Scraping course syllabus...", "running", workflow_step=1, workflow_total_steps=5)
    await asyncio.sleep(0.8)
    tracer.emit("atlas", "web_scraper", "Syllabus found — 14 topics identified", "done", workflow_step=1, workflow_total_steps=5,
        detail=build_mcp_detail("atlas", "web_scraper",
            steps=[{"title": "Fetch syllabus", "description": "Scraped course page with BeautifulSoup", "result_summary": "14 topics across 6 chapters", "tag": "14 topics", "tag_type": "success"}],
            state_writes=[{"key": "atlas_topics", "value_summary": "14 Python topics: OOP, decorators, async/await, data structures, testing, type hints, generators, context managers, metaclasses, descriptors, concurrency, packaging, debugging, profiling", "read_by": ["sage", "chrono", "dash"]}],
            raw_output_summary="14 topics across 6 chapters found", api_calls_made=1))
    await asyncio.sleep(0.2)

    tracer.emit("atlas", "tavily_search", "Searching resources for each topic...", "running", workflow_step=1, workflow_total_steps=5)
    await asyncio.sleep(1.0)
    tracer.emit("atlas", "tavily_search", "6 high-quality sources found", "done", workflow_step=1, workflow_total_steps=5,
        detail=build_mcp_detail("atlas", "tavily_search",
            steps=[{"title": "Multi-topic search", "description": "Queried Tavily for top 5 topics", "result_summary": "6 sources: Python docs, Real Python, CS50, Corey Schafer, Talk Python, ArXiv", "tag": "6 sources", "tag_type": "success"}],
            state_writes=[{"key": "atlas_research", "value_summary": "Summaries + key points for all 14 topics with citations", "read_by": ["sage"]}],
            raw_output_summary="Sources: Python docs, Real Python, CS50, Corey Schafer, Talk Python, ArXiv", api_calls_made=3))
    await asyncio.sleep(0.2)

    # Step 2 — Sage structures notes
    tracer.emit("sage", "filesystem", "Structuring study guide...", "running", workflow_step=2, workflow_total_steps=5)
    await asyncio.sleep(0.9)
    tracer.emit("sage", "filesystem", "14-page study guide created", "done", workflow_step=2, workflow_total_steps=5,
        detail=build_mcp_detail("sage", "filesystem",
            steps=[
                {"title": "Build note structure", "description": "Read atlas_topics + atlas_research from session state", "result_summary": "Structured 14 topics into 5 chapters with key points", "tag": "14 pages", "tag_type": "success"},
                {"title": "Save to Firestore",    "description": "Wrote to notes collection with tags: python, exam, study-guide", "result_summary": "All notes persisted", "tag": "Saved", "tag_type": "success"},
            ],
            state_writes=[{"key": "sage_notes_id", "value_summary": "Firestore note document ID", "read_by": ["mnemo"]}],
            memory_writes=[{"layer": "daily", "layer_display": "Daily log", "content": "Created Python exam study guide (14 topics)", "importance_score": 3}],
            api_calls_made=2))
    await asyncio.sleep(0.2)

    # Step 3 — ParallelAgent: Chrono + Dash simultaneously
    tracer.emit("chrono", "google_calendar", "Finding free slots tomorrow...", "running", workflow_step=3, workflow_total_steps=5)
    tracer.emit("dash",   "firestore",       "Building revision checklist...", "running", workflow_step=3, workflow_total_steps=5)
    await asyncio.sleep(1.1)

    tracer.emit("chrono", "google_calendar", "3 study blocks created — 1 conflict resolved", "done", workflow_step=3, workflow_total_steps=5,
        detail=build_mcp_detail("chrono", "google_calendar",
            steps=[
                {"title": "Read tomorrow's calendar", "description": "Listed all events for tomorrow", "result_summary": "3 free windows: 9–11am, 2–4pm, 7–9pm", "tag": "3 free slots", "tag_type": "info"},
                {"title": "Conflict check",           "description": "Detected Team standup at 10:00 overlapping slot 1", "result_summary": "Adjusted slot 1 start to 10:15am", "tag": "Conflict resolved", "tag_type": "warning"},
                {"title": "Create events",            "description": "Created 3 'Python Exam Study' calendar events", "result_summary": "Events at 9:00, 14:00, 19:00 with 15-min reminders", "tag": "3 events created", "tag_type": "success"},
            ],
            conflicts=[{"conflict": "Team standup at 10:00 overlaps 9–11am slot", "resolution": "Adjusted start to 10:15am", "resolution_type": "auto"}],
            state_writes=[{"key": "chrono_slots", "value_summary": "Study slots: 09:00, 14:00, 19:00", "read_by": ["mnemo"]}],
            api_calls_made=4))

    tracer.emit("dash", "firestore", "7 revision tasks created", "done", workflow_step=3, workflow_total_steps=5,
        detail=build_mcp_detail("dash", "firestore",
            steps=[{"title": "Generate task list", "description": "Grouped 14 topics into 7 revision tasks", "result_summary": "7 high-priority tasks due tomorrow", "tag": "7 tasks", "tag_type": "success"}],
            state_writes=[{"key": "dash_tasks", "value_summary": "7 revision tasks, high priority, due tomorrow", "read_by": ["mnemo"]}],
            api_calls_made=1))
    await asyncio.sleep(0.2)

    # Step 4 — Mnemo saves
    tracer.emit("mnemo", "firestore_memory", "Committing session to memory...", "running", workflow_step=4, workflow_total_steps=5)
    await asyncio.sleep(0.5)
    tracer.emit_memory_save("Saved: Python exam prep, 3 study slots, morning study preference")
    await asyncio.sleep(0.1)

    tracer.emit_workflow_complete("exam_prep")
    tracer.complete()

    return AgentResult(
        agent="nexus_core", agent_display_name="NEXUS Core",
        session_id=request.session_id, workflow_type="exam_prep",
        summary="Exam prep complete — study guide, 3 calendar blocks, 7 tasks ready",
        full_response="""## Exam Prep Complete

**Atlas** researched your Python syllabus — found **14 topics** across 6 chapters, sourced from Python docs, Real Python, and CS50.

**Sage** structured everything into a **14-page study guide** saved to your notes, organised by chapter with key points and code examples.

**Chrono** blocked **3 study sessions** for tomorrow:
- 9:00 – 10:15 AM *(adjusted — standup conflict resolved)*
- 2:00 – 4:00 PM
- 7:00 – 9:00 PM

**Dash** created **7 revision tasks**, all high priority, due tomorrow.

**Mnemo** saved your study preferences and schedule to memory.

You're ready. Good luck! 🎯""",
        from_demo_mode=True,
        suggestions=[
            SuggestionChip(label="Generate practice questions", prompt="Create 10 practice questions on Python OOP and decorators", agent_hint="atlas"),
            SuggestionChip(label="Add a final review slot",     prompt="Block 30 minutes the morning of my exam for final review", agent_hint="chrono"),
            SuggestionChip(label="Find video tutorials",        prompt="Find YouTube tutorials on Python async/await and decorators", agent_hint="atlas"),
        ],
    )


# ── Workflow: Day Planner ───────────────────────────────────

async def _demo_day_planner(request: ChatRequest, tracer: AgentTracer) -> AgentResult:
    tracer.emit_workflow_start("day_planner", 4)
    await asyncio.sleep(0.2)

    # Parallel fetch
    tracer.emit("dash",  "firestore",       "Loading pending tasks...",     "running", workflow_step=1, workflow_total_steps=4)
    tracer.emit("chrono","google_calendar", "Reading today's calendar...",  "running", workflow_step=1, workflow_total_steps=4)
    tracer.emit("flux",  "openweathermap",  "Checking today's weather...",  "running", workflow_step=1, workflow_total_steps=4)
    await asyncio.sleep(1.0)

    tracer.emit("dash",  "firestore",       "5 tasks loaded (2 high priority)", "done", workflow_step=1, workflow_total_steps=4,
        detail=build_mcp_detail("dash", "firestore",
            steps=[{"title": "Load pending tasks", "description": "Queried tasks where status=pending for demo-user", "result_summary": "5 tasks: 2 high, 2 medium, 1 low", "tag": "5 tasks", "tag_type": "info"}],
            raw_output_summary="Review PR (high), Write tests (high), Update docs (med), Sync prep (med), Code review (low)"))
    tracer.emit("chrono","google_calendar", "3 meetings, 2 free blocks today","done", workflow_step=1, workflow_total_steps=4,
        detail=build_mcp_detail("chrono", "google_calendar",
            steps=[{"title": "Read today's events", "description": "Listed calendar events for today", "result_summary": "Standup 10am, Design review 2pm, 1:1 4pm. Free: 11am–1pm, 5–7pm", "tag": "2 free blocks", "tag_type": "info"}],
            raw_output_summary="3 meetings, 2 focus windows available"))
    tracer.emit("flux",  "openweathermap",  "24°C, partly cloudy — great day", "done", workflow_step=1, workflow_total_steps=4,
        detail=build_mcp_detail("flux", "openweathermap",
            steps=[{"title": "Get weather", "description": "Called wttr.in for local weather", "result_summary": "24°C, partly cloudy, 0% rain chance", "tag": "Good conditions", "tag_type": "success"}],
            raw_output_summary="24°C, partly cloudy, light breeze"))
    await asyncio.sleep(0.3)

    tracer.emit("flux",   "firestore",       "Synthesising day plan...",     "running", workflow_step=2, workflow_total_steps=4)
    await asyncio.sleep(0.8)
    tracer.emit("flux",   "firestore",       "Day plan ready",               "done",    workflow_step=2, workflow_total_steps=4)
    tracer.emit("chrono", "google_calendar", "Creating focus time-blocks...", "running", workflow_step=3, workflow_total_steps=4)
    await asyncio.sleep(0.7)
    tracer.emit("chrono", "google_calendar", "2 focus blocks added",         "done",    workflow_step=3, workflow_total_steps=4)
    tracer.emit_memory_save("Saved: daily work pattern, prefers morning focus")
    tracer.emit_workflow_complete("day_planner")
    tracer.complete()

    return AgentResult(
        agent="nexus_core", agent_display_name="NEXUS Core",
        session_id=request.session_id, workflow_type="day_planner",
        summary="Day planned — 2 focus blocks created, 5 tasks prioritised",
        full_response="""## Your Day Plan

**Morning focus (11:00 AM – 1:00 PM)**
- Review PR *(high priority)*
- Write tests *(high priority)*

**Meetings** — Standup 10:00 AM · Design review 2:00 PM · 1:1 4:00 PM

**Afternoon focus (5:00 PM – 7:00 PM)**
- Update docs
- Prep for team sync

**Weather**: 24°C, partly cloudy — perfect for a lunch walk 🌤️

**Mnemo note**: Your peak focus is 10am–1pm based on your history.""",
        from_demo_mode=True,
        suggestions=[
            SuggestionChip(label="Set focus reminders", prompt="Remind me at 11am and 5pm to start focus blocks", agent_hint="chrono"),
            SuggestionChip(label="Plan the whole week",  prompt="Plan the rest of my week", agent_hint="chrono"),
            SuggestionChip(label="Defer low priority",   prompt="Move my low priority tasks to tomorrow", agent_hint="dash"),
        ],
    )


# ── Workflow: Research Loop ─────────────────────────────────

async def _demo_research(request: ChatRequest, tracer: AgentTracer) -> AgentResult:
    topic = request.prompt
    for drop in ["research", "find out", "look up", "what is", "explain", "tell me about"]:
        topic = topic.lower().replace(drop, "").strip()
    topic = topic.strip(" ?.,") or "the topic"

    tracer.emit_workflow_start("research_loop", 3)
    await asyncio.sleep(0.2)

    tracer.emit("atlas", "tavily_search", f"Searching: {topic[:40]}...", "running", workflow_step=1, workflow_total_steps=3)
    await asyncio.sleep(0.9)
    tracer.emit("atlas", "tavily_search", "5 sources found", "done", workflow_step=1, workflow_total_steps=3,
        detail=build_mcp_detail("atlas", "tavily_search",
            steps=[{"title": "Primary search", "description": f"Searched Tavily for '{topic}'", "result_summary": "5 high-quality sources found", "tag": "5 sources", "tag_type": "success"}],
            state_writes=[{"key": "atlas_research", "value_summary": f"Research summaries on {topic}", "read_by": ["sage"]}],
            api_calls_made=2))

    tracer.emit("atlas", "wikipedia", "Retrieving Wikipedia article...", "running", workflow_step=1, workflow_total_steps=3)
    await asyncio.sleep(0.6)
    tracer.emit("atlas", "wikipedia", "Wikipedia article retrieved (2,100 words)", "done", workflow_step=1, workflow_total_steps=3,
        detail=build_mcp_detail("atlas", "wikipedia",
            steps=[{"title": "Wikipedia lookup", "description": f"Retrieved article for '{topic}'", "result_summary": "2,100-word article, 12 citations", "tag": "Retrieved", "tag_type": "success"}],
            api_calls_made=1))
    await asyncio.sleep(0.2)

    tracer.emit("sage", "filesystem", "Structuring research notes...", "running", workflow_step=2, workflow_total_steps=3)
    await asyncio.sleep(0.8)
    tracer.emit("sage", "filesystem", "Research notes saved — 4 sections", "done", workflow_step=2, workflow_total_steps=3,
        detail=build_mcp_detail("sage", "filesystem",
            steps=[{"title": "Build note", "description": "Structured into: Intro, Key Concepts, Examples, Further Reading", "result_summary": "4-section note saved to Firestore", "tag": "Saved", "tag_type": "success"}],
            memory_writes=[{"layer": "profile", "layer_display": "Long-term profile", "content": f"User researched: {topic}", "importance_score": 4}],
            api_calls_made=1))

    tracer.emit_memory_save(f"Saved research interest: '{topic[:30]}'")
    tracer.emit_workflow_complete("research_loop")
    tracer.complete()

    return AgentResult(
        agent="nexus_core", agent_display_name="NEXUS Core",
        session_id=request.session_id, workflow_type="research_loop",
        summary=f"Research on '{topic}' complete — notes saved from 6 sources",
        full_response=f"""## Research: {topic.title()}

**Atlas** searched Tavily, Brave, and Wikipedia — **6 high-quality sources** found.

**Key findings:**
- Wikipedia article: 2,100 words, 12 citations
- 5 additional sources: practical examples and real-world use cases
- Quality score: **8.5 / 10** ✓

**Sage** saved a **4-section note** to your knowledge base:
1. Introduction & Overview
2. Key Concepts
3. Practical Examples
4. Further Reading & Resources

**Mnemo** tagged your interest in this topic — related notes will surface automatically in future sessions.""",
        from_demo_mode=True,
        suggestions=[
            SuggestionChip(label="Go deeper",          prompt=f"Explain the most important concept in {topic} in detail", agent_hint="atlas"),
            SuggestionChip(label="Find video resources",prompt=f"Find YouTube tutorials explaining {topic}", agent_hint="atlas"),
            SuggestionChip(label="Create a study plan", prompt=f"Create a 7-day learning plan for {topic}", agent_hint="quest"),
        ],
    )


# ── Workflow: Add Task ──────────────────────────────────────

async def _demo_add_task(request: ChatRequest, tracer: AgentTracer) -> AgentResult:
    tracer.emit("dash", "firestore", "Creating task...", "running")
    await asyncio.sleep(0.5)
    tracer.emit("dash", "firestore", "Task created", "done",
        detail=build_mcp_detail("dash", "firestore",
            steps=[{"title": "Create task", "description": f"Parsed: '{request.prompt[:50]}'", "result_summary": "Task created, medium priority", "tag": "Created", "tag_type": "success"}],
            memory_writes=[{"layer": "daily", "layer_display": "Daily log", "content": f"Added task: {request.prompt[:40]}", "importance_score": 2}],
            api_calls_made=1))
    tracer.emit_memory_save("Daily log updated")
    tracer.complete()

    return AgentResult(
        agent="dash", agent_display_name="Dash",
        session_id=request.session_id, workflow_type="simple",
        summary="Task created",
        full_response=f"""## Task Created ✓

> {request.prompt}

- **Priority**: Medium
- **Status**: Pending
- **Added**: Just now

Ready in your task list. Want me to schedule time for it?""",
        from_demo_mode=True,
        suggestions=[
            SuggestionChip(label="Schedule time for this", prompt=f"Find time for: {request.prompt[:40]}", agent_hint="chrono"),
            SuggestionChip(label="Make it high priority",  prompt=f"Set high priority: {request.prompt[:40]}", agent_hint="dash"),
            SuggestionChip(label="See all tasks",          prompt="Show me all my pending tasks", agent_hint="dash"),
        ],
    )


# ── Workflow: Adaptive ──────────────────────────────────────

async def _demo_adaptive(request: ChatRequest, tracer: AgentTracer) -> AgentResult:
    tracer.emit("flux", "firestore", "Reading your current workload...", "running")
    await asyncio.sleep(0.5)
    tracer.emit("flux", "firestore", "Heavy day detected — reducing load", "done",
        detail=build_mcp_detail("flux", "firestore",
            steps=[{"title": "Assess workload", "description": "Read pending tasks + calendar density", "result_summary": "8 tasks + 4 meetings — heavy day", "tag": "Heavy day", "tag_type": "warning"}],
            api_calls_made=2))

    tracer.emit("dash", "firestore", "Rescheduling low-priority tasks...", "running")
    await asyncio.sleep(0.6)
    tracer.emit("dash", "firestore", "3 tasks moved to tomorrow", "done",
        detail=build_mcp_detail("dash", "firestore",
            steps=[{"title": "Reschedule", "description": "Moved 3 low-priority tasks to tomorrow", "result_summary": "Today reduced to 5 tasks", "tag": "3 rescheduled", "tag_type": "success"}],
            api_calls_made=3))

    tracer.emit_memory_save("Noted: stress signal, user prefers lighter days")
    tracer.complete()

    return AgentResult(
        agent="flux", agent_display_name="Flux",
        session_id=request.session_id, workflow_type="simple",
        summary="Workload lightened — 3 tasks moved, today is manageable",
        full_response="""## Let's make today easier 💙

Heard you. You had 8 tasks and 4 meetings. Let's fix that.

**Dash** moved **3 low-priority tasks** to tomorrow:
- Update docs
- Code review (non-urgent)
- Weekly report draft

**Today's list** (5 things):
1. Review PR *(high — keep)*
2. Write tests *(high — keep)*
3. Sync prep *(needed for 2pm)*
4. Design review *(2pm — just show up)*
5. 1:1 *(4pm — just show up)*

That's it. One thing at a time. You've got this. 🌱""",
        from_demo_mode=True,
        suggestions=[
            SuggestionChip(label="See tomorrow's new list", prompt="What's on my plate tomorrow?", agent_hint="dash"),
            SuggestionChip(label="Block quiet time today",  prompt="Block 30 minutes of no-meeting quiet time today", agent_hint="chrono"),
            SuggestionChip(label="Set a hard stop",        prompt="Block 6pm as my hard stop for today", agent_hint="chrono"),
        ],
    )


# ── Workflow: General ───────────────────────────────────────

async def _demo_general(request: ChatRequest, tracer: AgentTracer) -> AgentResult:
    tracer.emit("nexus_core", "workflow_engine", "Analysing your request...", "running")
    await asyncio.sleep(0.3)
    tracer.emit("atlas", "tavily_search", "Gathering information...", "running")
    await asyncio.sleep(0.7)
    tracer.emit("atlas", "tavily_search", "Information gathered", "done",
        detail=build_mcp_detail("atlas", "tavily_search",
            steps=[{"title": "General search", "description": f"Searched: '{request.prompt[:50]}'", "result_summary": "3 relevant sources found", "tag": "3 sources", "tag_type": "info"}],
            api_calls_made=1))
    tracer.emit_memory_save("Logged query to daily log")
    tracer.complete()

    return AgentResult(
        agent="nexus_core", agent_display_name="NEXUS Core",
        session_id=request.session_id, workflow_type="simple",
        summary="Here's what I found",
        full_response=f"""## Response

I've looked into: *"{request.prompt}"*

For richer results, try one of these proven prompts:
- *"Prepare for my [exam/interview]"* — full 5-agent workflow
- *"Plan my day"* — calendar + tasks + weather in one brief
- *"Research [topic] and make notes"* — deep research saved to your knowledge base
- *"I'm feeling overwhelmed"* — intelligent workload reduction

What would you like to do?""",
        from_demo_mode=True,
        suggestions=[
            SuggestionChip(label="Prepare for an exam",  prompt="Prepare for my Python exam tomorrow", agent_hint="atlas"),
            SuggestionChip(label="Plan my day",          prompt="Plan my day", agent_hint="flux"),
            SuggestionChip(label="Research something",   prompt=f"Research {request.prompt[:30]} and make notes", agent_hint="atlas"),
        ],
    )


# ─────────────────────────────────────────────
# LIVE ORCHESTRATOR — Phase 6
# ─────────────────────────────────────────────

async def _live_orchestrate(request: ChatRequest, tracer: AgentTracer) -> AgentResult:
    """
    Real ADK orchestration — implemented in Phase 6.
    Falls back to demo mode until agents are ready.
    """
    # TODO Phase 6:
    # from agents.orchestrator import run_orchestrator
    # return await run_orchestrator(request, tracer)
    print("[LIVE] Real orchestrator not yet implemented — using demo mode")
    return await _demo_orchestrate(request, tracer)


# ─────────────────────────────────────────────
# DEMO MEMORY
# ─────────────────────────────────────────────

def _demo_memory(user_id: str) -> UserMemory:
    return UserMemory(
        user_id=user_id,
        working={
            "atlas_topics":  ["OOP", "decorators", "async/await", "data structures"],
            "chrono_slots":  ["09:00", "14:00", "19:00"],
            "mood_score":    7,
            "active_workflow": "exam_prep",
        },
        daily=[
            MemoryEntry(user_id=user_id, layer="daily", content="Ran exam prep workflow for Python exam", agent_source="nexus_core", importance_score=4, tags=["exam", "python"]),
            MemoryEntry(user_id=user_id, layer="daily", content="Chrono created 3 study blocks (1 conflict resolved)", agent_source="chrono", importance_score=3, tags=["calendar"]),
            MemoryEntry(user_id=user_id, layer="daily", content="Sage created 14-page Python study guide", agent_source="sage", importance_score=4, tags=["notes", "python"]),
            MemoryEntry(user_id=user_id, layer="daily", content="Atlas researched 6 sources on Python syllabus", agent_source="atlas", importance_score=3, tags=["research"]),
        ],
        profile=[
            MemoryEntry(user_id=user_id, layer="profile", content="Prefers morning study sessions (9am–11am)", agent_source="mnemo", importance_score=4, tags=["preference"]),
            MemoryEntry(user_id=user_id, layer="profile", content="Peak productivity: Tuesday and Thursday mornings", agent_source="mnemo", importance_score=4, tags=["pattern"]),
            MemoryEntry(user_id=user_id, layer="profile", content="Currently studying Python — exam scheduled", agent_source="mnemo", importance_score=5, tags=["goal", "python"]),
            MemoryEntry(user_id=user_id, layer="profile", content="Prefers bullet-point summaries over long paragraphs", agent_source="mnemo", importance_score=3, tags=["preference"]),
        ],
        semantic_results=[
            MemoryEntry(user_id=user_id, layer="semantic", content="Python OOP study notes — created today (similarity: 0.94)", agent_source="sage", tags=["python", "notes"]),
            MemoryEntry(user_id=user_id, layer="semantic", content="Decorator patterns reference — 3 weeks ago (similarity: 0.81)", agent_source="sage", tags=["python", "notes"]),
        ],
    )


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
