"""
logic/orchestration.py — Demo Workflow Functions

This module provides demo workflow responses for the NEXUS system.
The actual orchestration is handled by SwarmEngine in orchestrator.py.
"""

import asyncio
import logging

from nexus.models.schemas import (
    ChatRequest,
    AgentResult,
    SuggestionChip,
)
from nexus.observability.agent_tracer import AgentTracer

logger = logging.getLogger("nexus")


async def run_demo_workflow(
    request: ChatRequest, tracer: AgentTracer, intent: str
) -> AgentResult:
    """Route to appropriate demo workflow based on intent."""

    if intent == "exam_prep":
        return await _demo_exam_prep(request, tracer)
    elif intent == "day_planner":
        return await _demo_day_planner(request, tracer)
    elif intent == "research_loop":
        return await _demo_research(request, tracer)
    elif intent == "add_task":
        return await _demo_add_task(request, tracer)
    elif intent == "adaptive":
        return await _demo_adaptive(request, tracer)
    else:
        return await _demo_general(request, tracer)


async def _demo_exam_prep(request: ChatRequest, tracer: AgentTracer) -> AgentResult:
    tracer.emit_workflow_start("exam_prep", 5)
    await asyncio.sleep(0.3)

    tracer.emit(
        "atlas",
        "web_scraper",
        "Scraping course syllabus...",
        "running",
        workflow_step=1,
        workflow_total_steps=5,
    )
    await asyncio.sleep(0.8)
    tracer.emit(
        "atlas",
        "web_scraper",
        "Syllabus found — 14 topics identified",
        "done",
        workflow_step=1,
        workflow_total_steps=5,
    )

    tracer.emit_workflow_complete("exam_prep")
    tracer.complete()

    return AgentResult(
        agent="orchestrator",
        session_id=request.session_id,
        workflow_type="exam_prep",
        summary="Exam prep complete",
        markdown_content="## Exam Prep Complete\n\n**Research** researched your Python syllabus — found **14 topics**.\n\nYou're ready!",
        suggestions=[
            SuggestionChip(
                label="Find video tutorials",
                prompt="Find YouTube tutorials on Python",
                agent_hint="atlas",
            ),
        ],
    )


async def _demo_day_planner(request: ChatRequest, tracer: AgentTracer) -> AgentResult:
    tracer.emit_workflow_start("day_planner", 4)
    await asyncio.sleep(0.2)

    tracer.emit(
        "chrono",
        "google_calendar",
        "Reading today's calendar...",
        "running",
        workflow_step=1,
        workflow_total_steps=4,
    )
    await asyncio.sleep(1.0)
    tracer.emit(
        "chrono",
        "google_calendar",
        "3 meetings, 2 free blocks today",
        "done",
        workflow_step=1,
        workflow_total_steps=4,
    )

    tracer.emit_workflow_complete("day_planner")
    tracer.complete()

    return AgentResult(
        agent="orchestrator",
        session_id=request.session_id,
        workflow_type="day_planner",
        summary="Day planned",
        markdown_content="## Your Day Plan\n\n**Morning focus (11:00 AM – 1:00 PM)**\n\n**Meetings** — Standup 10:00 AM · Design review 2:00 PM",
        suggestions=[],
    )


async def _demo_research(request: ChatRequest, tracer: AgentTracer) -> AgentResult:
    topic = request.prompt
    for drop in [
        "research",
        "find out",
        "look up",
        "what is",
        "explain",
        "tell me about",
    ]:
        topic = topic.lower().replace(drop, "").strip()
    topic = topic.strip(" ?.,") or "the topic"

    tracer.emit_workflow_start("research_loop", 3)
    await asyncio.sleep(0.2)
    tracer.emit(
        "atlas",
        "tavily_search",
        f"Searching: {topic[:40]}...",
        "running",
        workflow_step=1,
        workflow_total_steps=3,
    )
    await asyncio.sleep(0.9)
    tracer.emit(
        "atlas",
        "tavily_search",
        "5 sources found",
        "done",
        workflow_step=1,
        workflow_total_steps=3,
    )

    tracer.emit_workflow_complete("research_loop")
    tracer.complete()

    return AgentResult(
        agent="orchestrator",
        session_id=request.session_id,
        workflow_type="research_loop",
        summary=f"Research on '{topic}' complete",
        markdown_content=f"## Research: {topic.title()}\n\n**Atlas** searched — **5 sources** found.",
        suggestions=[
            SuggestionChip(
                label="Go deeper",
                prompt=f"Explain {topic} in detail",
                agent_hint="atlas",
            ),
        ],
    )


async def _demo_add_task(request: ChatRequest, tracer: AgentTracer) -> AgentResult:
    tracer.emit("tasks", "firestore", "Creating task...", "running")
    await asyncio.sleep(0.5)
    tracer.emit("tasks", "firestore", "Task created", "done")
    tracer.complete()

    return AgentResult(
        agent="tasks",
        session_id=request.session_id,
        workflow_type="simple",
        summary="Task created",
        markdown_content=f"## Task Created\n\n> {request.prompt}\n\n- **Priority**: Medium\n- **Status**: Pending",
        suggestions=[],
    )


async def _demo_adaptive(request: ChatRequest, tracer: AgentTracer) -> AgentResult:
    tracer.emit("briefing", "firestore", "Reading your current workload...", "running")
    await asyncio.sleep(0.5)
    tracer.emit("briefing", "firestore", "Heavy day detected — reducing load", "done")
    tracer.complete()

    return AgentResult(
        agent="briefing",
        session_id=request.session_id,
        workflow_type="simple",
        summary="Workload lightened",
        markdown_content="## Let's make today easier\n\nHeard you. Let's simplify your day.",
        suggestions=[],
    )


async def _demo_general(request: ChatRequest, tracer: AgentTracer) -> AgentResult:
    tracer.emit(
        "orchestrator", "workflow_engine", "Analysing your request...", "running"
    )
    await asyncio.sleep(0.3)
    tracer.complete()

    return AgentResult(
        agent="orchestrator",
        session_id=request.session_id,
        workflow_type="simple",
        summary="Here's what I found",
        markdown_content=f'I\'ve looked into: *"{request.prompt}"*\n\nWhat would you like to do?',
        suggestions=[
            SuggestionChip(
                label="Prepare for an exam",
                prompt="Prepare for my Python exam",
                agent_hint="atlas",
            ),
            SuggestionChip(
                label="Plan my day", prompt="Plan my day", agent_hint="chrono"
            ),
        ],
    )
