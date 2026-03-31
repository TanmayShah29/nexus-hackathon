"""
observability/agent_tracer.py — NEXUS Live Agent Trace System (Fixed)
"""
from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional, Any

from nexus.models.schemas import (
    TraceEvent, MCPCardDetail, MCPStep,
    StateWrite, MemoryWrite, ConflictResolution,
    AgentName, TraceStatus, AGENT_IDENTITY_MAP,
)

# FIX: Module-level Supabase import — not imported on every emit() call
from nexus.memory.supabase_client import get_supabase_client


class AgentTracer:
    """Per-request trace manager — feeds the SSE stream."""

    def __init__(self, session_id: str, request_id: str = None):
        self.session_id = session_id
        self.request_id = request_id
        self._events: list[TraceEvent] = []
        self._queue: asyncio.Queue[TraceEvent | None] = asyncio.Queue()
        self._active_tools: dict[str, float] = {}
        self._completed = False
        self._created_at = datetime.now(timezone.utc).isoformat()

    def cleanup(self):
        if self._completed:
            return
        self._events.clear()
        self._active_tools.clear()
        self._completed = True
        try:
            self._queue.put_nowait(None)
        except (asyncio.QueueFull, RuntimeError):
            pass

    # ── Emit ──────────────────────────────────────────────────

    def emit(
        self,
        agent: AgentName,
        tool: str,
        action: str,
        status: TraceStatus,
        detail: Optional[MCPCardDetail] = None,
        workflow_step: Optional[int] = None,
        workflow_total_steps: Optional[int] = None,
        resource_id: Optional[str] = None,
        resource_link: Optional[str] = None,
    ) -> TraceEvent:
        tool_key = f"{agent}:{tool}"
        if status == "running":
            self._active_tools[tool_key] = time.time()

        duration_ms = None
        if status in ("done", "error") and tool_key in self._active_tools:
            duration_ms = int((time.time() - self._active_tools.pop(tool_key)) * 1000)
            if detail:
                detail.duration_ms = duration_ms

        agent_info = AGENT_IDENTITY_MAP.get(agent)
        agent_display = agent_info.display_name if agent_info else agent.title()

        event = TraceEvent(
            session_id=self.session_id,
            agent=agent,
            agent_display_name=agent_display,
            tool=tool,
            tool_display_name=_tool_display_name(tool),
            action=action,
            status=status,
            detail=detail,
            workflow_step=workflow_step,
            workflow_total_steps=workflow_total_steps,
        )

        self._events.append(event)
        self._queue.put_nowait(event)

        # FIX: get_supabase_client() is a module-level import — no per-call overhead
        try:
            sb = get_supabase_client()
            if sb.is_active():
                sb.log_trace(
                    thread_id=self.session_id,
                    agent_id=agent,
                    status=status,
                    message=action,
                )
        except Exception:
            pass  # Tracing must never crash the request

        return event

    def emit_workflow_start(self, workflow_type: str, total_steps: int):
        self.emit(
            agent="orchestrator",
            tool="workflow_engine",
            action=f"Starting {workflow_type.replace('_', ' ')} ({total_steps} steps)",
            status="running",
            workflow_step=0,
            workflow_total_steps=total_steps,
        )

    def emit_workflow_complete(self, workflow_type: str):
        self.emit(
            agent="orchestrator",
            tool="workflow_engine",
            action="Workflow complete",
            status="done",
        )

    def emit_memory_save(self, summary: str):
        self.emit(agent="mnemo", tool="firestore_memory", action=summary, status="done")

    def complete(self):
        self._completed = True
        self._queue.put_nowait(None)

    # ── Stream ────────────────────────────────────────────────

    async def stream(self) -> AsyncGenerator[str, None]:
        while True:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=30.0)
            except asyncio.TimeoutError:
                yield 'data: {"type": "heartbeat"}\n\n'
                continue

            if event is None:
                yield 'data: {"type": "complete"}\n\n'
                break

            yield self._format_sse(event)

    def _format_sse(self, event: TraceEvent) -> str:
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
            "resource_id": event.detail.resource_id if event.detail else None,
            "resource_link": event.detail.resource_link if event.detail else None,
            "detail": event.detail.model_dump()
            if event.detail and event.status == "done"
            else None,
        }
        return f"data: {json.dumps(payload)}\n\n"

    # ── Query ─────────────────────────────────────────────────

    def get_trace(self) -> dict[str, Any]:
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
        for event in reversed(self._events):
            if event.tool == tool and event.detail is not None:
                return event.detail
        return None

    def get_events_for_agent(self, agent: AgentName) -> list[TraceEvent]:
        return [e for e in self._events if e.agent == agent]

    def __len__(self) -> int:
        return len(self._events)


# ── Trace Store ───────────────────────────────────────────────

class TraceStore:
    """Global in-memory registry — keeps last 100 sessions."""

    def __init__(self, max_sessions: int = 100):
        self._store: dict[str, AgentTracer] = {}
        self._order: deque[str] = deque()
        self._max = max_sessions

    def create(self, session_id: str) -> AgentTracer:
        tracer = AgentTracer(session_id)
        self._store[session_id] = tracer
        self._order.append(session_id)
        if len(self._order) > self._max:
            oldest = self._order.popleft()
            self._store.pop(oldest, None)
        return tracer

    def get(self, session_id: str) -> Optional[AgentTracer]:
        return self._store.get(session_id)

    def __len__(self) -> int:
        return len(self._store)


trace_store = TraceStore()


# ── Helpers ───────────────────────────────────────────────────

def _tool_display_name(tool: str) -> str:
    NAMES = {
        "tavily_search": "Tavily Search",
        "brave_search": "Brave Search",
        "wikipedia": "Wikipedia",
        "youtube_transcript": "YouTube Transcript",
        "web_scraper": "Web Scraper",
        "google_calendar": "Google Calendar",
        "google_maps": "Google Maps",
        "openweathermap": "OpenWeatherMap",
        "google_drive": "Google Drive",
        "filesystem": "File System",
        "notion": "Notion",
        "firestore": "Firestore",
        "firestore_memory": "Memory (Firestore)",
        "firestore_vector": "Semantic Search",
        "python_executor": "Python Executor",
        "workflow_engine": "Workflow Engine",
        "gmail": "Gmail",
    }
    return NAMES.get(tool, tool.replace("_", " ").title())


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
    agent_info = AGENT_IDENTITY_MAP.get(agent)
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
                title=s.get("title", f"Step {i + 1}"),
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
