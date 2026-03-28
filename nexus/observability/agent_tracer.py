"""
agent_tracer.py — NEXUS Live Agent Trace System

This is the system that makes the UI come alive.
Every agent call goes through the tracer.
It emits Server-Sent Events (SSE) that the frontend consumes
to update the left rail MCP cards, the agent graph, and the right rail
in real time — all while the workflow is still running.

Usage:
    tracer = AgentTracer(session_id="abc-123")

    tracer.emit("atlas", "tavily_search", "Searching for Python topics...", "running")
    # ... agent does its work ...
    tracer.emit("atlas", "tavily_search", "Found 14 topics", "done", detail={...})

    # In FastAPI SSE endpoint:
    async for chunk in tracer.stream():
        yield chunk
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime
from typing import AsyncGenerator, Optional, Any

from models.schemas import (
    TraceEvent, MCPCardDetail, MCPStep, StateWrite, MemoryWrite,
    ConflictResolution, AgentName, TraceStatus, AGENT_MAP
)


class AgentTracer:
    """
    Per-request trace manager.

    Lifecycle:
        1. Created at the start of each /chat request
        2. Passed down to orchestrator and all agents
        3. Every agent emits events through it
        4. FastAPI SSE endpoint streams it to the frontend
        5. Stored in memory for GET /trace/{session_id} lookup
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._events: list[TraceEvent] = []
        self._queue: asyncio.Queue[TraceEvent | None] = asyncio.Queue()
        self._active_tools: dict[str, float] = {}   # tool_key → start_time
        self._completed = False
        self._created_at = datetime.utcnow().isoformat()

    # ─────────────────────────────────────────
    # EMIT — called by agents to fire an event
    # ─────────────────────────────────────────

    def emit(
        self,
        agent: AgentName,
        tool: str,
        action: str,
        status: TraceStatus,
        detail: Optional[MCPCardDetail] = None,
        workflow_step: Optional[int] = None,
        workflow_total_steps: Optional[int] = None,
    ) -> TraceEvent:
        """
        Emit one trace event.
        Immediately available in the SSE stream and stored in trace history.

        Args:
            agent:       Agent name e.g. "atlas"
            tool:        MCP tool key e.g. "tavily_search"
            action:      Human-readable description e.g. "Searching for Python topics..."
            status:      "running" | "done" | "error" | "skipped"
            detail:      Full MCPCardDetail shown when user clicks the card
            workflow_step: Current step number in a pipeline (optional)
            workflow_total_steps: Total steps in the pipeline (optional)
        """
        # Track timing
        tool_key = f"{agent}:{tool}"
        if status == "running":
            self._active_tools[tool_key] = time.time()

        duration_ms = None
        if status in ("done", "error") and tool_key in self._active_tools:
            duration_ms = int((time.time() - self._active_tools.pop(tool_key)) * 1000)
            if detail:
                detail.duration_ms = duration_ms

        # Resolve display names from registry
        agent_info = AGENT_MAP.get(agent)
        agent_display = agent_info.display_name if agent_info else agent.title()
        tool_display = _tool_display_name(tool)

        event = TraceEvent(
            session_id=self.session_id,
            agent=agent,
            agent_display_name=agent_display,
            tool=tool,
            tool_display_name=tool_display,
            action=action,
            status=status,
            detail=detail,
            workflow_step=workflow_step,
            workflow_total_steps=workflow_total_steps,
        )

        self._events.append(event)
        self._queue.put_nowait(event)
        return event

    def emit_workflow_start(self, workflow_type: str, total_steps: int):
        """Special event to tell the frontend a multi-step workflow is starting"""
        self.emit(
            agent="nexus_core",
            tool="workflow_engine",
            action=f"Starting {workflow_type.replace('_', ' ')} workflow ({total_steps} steps)",
            status="running",
            workflow_step=0,
            workflow_total_steps=total_steps,
        )

    def emit_workflow_complete(self, workflow_type: str):
        """Special event to tell the frontend the workflow is done"""
        self.emit(
            agent="nexus_core",
            tool="workflow_engine",
            action=f"Workflow complete",
            status="done",
        )

    def emit_memory_save(self, summary: str):
        """Mnemo saved something — makes her card glow purple in the UI"""
        self.emit(
            agent="mnemo",
            tool="firestore_memory",
            action=summary,
            status="done",
        )

    def complete(self):
        """Signal that the stream is finished — closes the SSE connection"""
        self._completed = True
        self._queue.put_nowait(None)   # sentinel value

    # ─────────────────────────────────────────
    # STREAM — async generator for FastAPI SSE
    # ─────────────────────────────────────────

    async def stream(self) -> AsyncGenerator[str, None]:
        """
        Async generator that yields SSE-formatted strings.

        Used in FastAPI like:
            async def chat_endpoint():
                return EventSourceResponse(tracer.stream())

        Each chunk is formatted as:
            data: {"agent": "atlas", "tool": "tavily_search", ...}\n\n

        The frontend's EventSource listener receives these and updates the UI.
        """
        while True:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=30.0)
            except asyncio.TimeoutError:
                # Send a heartbeat to keep the connection alive
                yield "data: {\"type\": \"heartbeat\"}\n\n"
                continue

            if event is None:
                # Sentinel — stream is done
                yield "data: {\"type\": \"complete\"}\n\n"
                break

            yield self._format_sse(event)

    def _format_sse(self, event: TraceEvent) -> str:
        """Format a TraceEvent as an SSE data chunk"""
        payload = {
            "type": "trace",
            "event_id": event.event_id,
            "session_id": event.session_id,
            "timestamp": event.timestamp,
            "agent": event.agent,
            "agent_display_name": event.agent_display_name,
            "tool": event.tool,
            "tool_display_name": event.tool_display_name,
            "action": event.action,
            "status": event.status,
            "workflow_step": event.workflow_step,
            "workflow_total_steps": event.workflow_total_steps,
            # Include detail only if status is done (reduces payload size during running)
            "detail": event.detail.model_dump() if event.detail and event.status == "done" else None,
        }
        return f"data: {json.dumps(payload)}\n\n"

    # ─────────────────────────────────────────
    # QUERY — for GET /trace/{session_id}
    # ─────────────────────────────────────────

    def get_trace(self) -> dict[str, Any]:
        """
        Return the full trace for a completed session.
        Used by GET /trace/{session_id} — also powers the MCP card detail drawer.
        """
        return {
            "session_id": self.session_id,
            "created_at": self._created_at,
            "completed": self._completed,
            "total_events": len(self._events),
            "agents_involved": list({e.agent for e in self._events}),
            "tools_called": list({e.tool for e in self._events}),
            "events": [e.model_dump() for e in self._events],
        }

    def get_mcp_detail(self, tool: str) -> Optional[MCPCardDetail]:
        """
        Get the MCPCardDetail for a specific tool call.
        Used by GET /mcp-detail/{session_id}/{tool}
        Powers the MCP card detail drawer when user clicks a completed card.
        """
        for event in reversed(self._events):
            if event.tool == tool and event.detail is not None:
                return event.detail
        return None

    def get_events_for_agent(self, agent: AgentName) -> list[TraceEvent]:
        """Get all events for a specific agent"""
        return [e for e in self._events if e.agent == agent]

    def __len__(self) -> int:
        return len(self._events)

    def __repr__(self) -> str:
        return f"AgentTracer(session_id={self.session_id!r}, events={len(self._events)})"


# ─────────────────────────────────────────────────────
# TRACE STORE — in-memory registry of all active traces
# ─────────────────────────────────────────────────────

class TraceStore:
    """
    Global registry of all AgentTracer instances.
    Keeps the last 100 sessions in memory.

    Used by:
        - /chat endpoint: creates and registers a tracer
        - /trace/{id}: looks up a tracer by session_id
        - /mcp-detail/{id}/{tool}: looks up a specific MCP call
    """

    def __init__(self, max_sessions: int = 100):
        self._store: dict[str, AgentTracer] = {}
        self._order: list[str] = []
        self._max = max_sessions

    def create(self, session_id: str) -> AgentTracer:
        """Create a new tracer and register it"""
        tracer = AgentTracer(session_id)
        self._store[session_id] = tracer
        self._order.append(session_id)
        # Evict oldest if over limit
        if len(self._order) > self._max:
            oldest = self._order.pop(0)
            self._store.pop(oldest, None)
        return tracer

    def get(self, session_id: str) -> Optional[AgentTracer]:
        """Look up a tracer by session_id"""
        return self._store.get(session_id)

    def __len__(self) -> int:
        return len(self._store)


# Global singleton — imported by main.py and all agents
trace_store = TraceStore()


# ─────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────

def _tool_display_name(tool: str) -> str:
    """Convert tool key to human-readable display name"""
    DISPLAY_NAMES = {
        "tavily_search":     "Tavily Search",
        "brave_search":      "Brave Search",
        "wikipedia":         "Wikipedia",
        "youtube_transcript":"YouTube Transcript",
        "web_scraper":       "Web Scraper",
        "google_calendar":   "Google Calendar",
        "google_maps":       "Google Maps",
        "openweathermap":    "OpenWeatherMap",
        "google_drive":      "Google Drive",
        "filesystem":        "File System",
        "notion":            "Notion",
        "firestore":         "Firestore",
        "firestore_memory":  "Memory (Firestore)",
        "firestore_vector":  "Semantic Search",
        "python_executor":   "Python Executor",
        "workflow_engine":   "Workflow Engine",
        "gmail":             "Gmail",
    }
    return DISPLAY_NAMES.get(tool, tool.replace("_", " ").title())


def build_mcp_detail(
    agent: AgentName,
    tool: str,
    steps: list[dict],
    state_writes: Optional[list[dict]] = None,
    memory_writes: Optional[list[dict]] = None,
    conflicts: Optional[list[dict]] = None,
    raw_output_summary: Optional[str] = None,
    api_calls_made: int = 1,
) -> MCPCardDetail:
    """
    Helper to build an MCPCardDetail cleanly.
    Used by MCP server wrappers to build the detail object
    that gets attached to TraceEvents.

    Args:
        agent:  Agent name
        tool:   Tool key
        steps:  List of dicts with keys: title, description, result_summary, tag, tag_type
        state_writes: List of dicts with keys: key, value_summary, read_by
        memory_writes: List of dicts with keys: layer, layer_display, content, importance_score
        conflicts: List of dicts with keys: conflict, resolution, resolution_type
        raw_output_summary: One-line summary of the raw tool output
        api_calls_made: Number of API calls made

    Example:
        detail = build_mcp_detail(
            agent="atlas",
            tool="tavily_search",
            steps=[
                {
                    "title": "Step 1 — Search for Python OOP topics",
                    "description": "Called Tavily API with query 'Python OOP syllabus'",
                    "result_summary": "Found 14 topics across 6 sources",
                    "tag": "14 topics found",
                    "tag_type": "success",
                }
            ],
            state_writes=[
                {
                    "key": "atlas_topics",
                    "value_summary": "List of 14 Python OOP topics",
                    "read_by": ["sage", "chrono"],
                }
            ],
            raw_output_summary="14 topics: OOP, decorators, async/await, data structures...",
            api_calls_made=2,
        )
    """
    agent_info = AGENT_MAP.get(agent)
    agent_display = agent_info.display_name if agent_info else agent.title()

    return MCPCardDetail(
        agent=agent,
        agent_display_name=agent_display,
        tool=tool,
        tool_display_name=_tool_display_name(tool),
        api_calls_made=api_calls_made,
        status="done",
        steps=[
            MCPStep(
                step_number=i + 1,
                title=s.get("title", f"Step {i+1}"),
                description=s.get("description", ""),
                api_endpoint=s.get("api_endpoint"),
                result_summary=s.get("result_summary"),
                tag=s.get("tag"),
                tag_type=s.get("tag_type"),
            )
            for i, s in enumerate(steps)
        ],
        session_state_writes=[
            StateWrite(
                key=w["key"],
                value_summary=w["value_summary"],
                written_by=agent,
                read_by=w.get("read_by"),
            )
            for w in (state_writes or [])
        ],
        memory_writes=[
            MemoryWrite(
                layer=m["layer"],
                layer_display=m["layer_display"],
                content=m["content"],
                importance_score=m.get("importance_score"),
            )
            for m in (memory_writes or [])
        ],
        conflicts_resolved=[
            ConflictResolution(
                conflict=c["conflict"],
                resolution=c["resolution"],
                resolution_type=c.get("resolution_type", "auto"),
            )
            for c in (conflicts or [])
        ],
        raw_output_summary=raw_output_summary,
    )
