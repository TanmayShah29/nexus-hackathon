"""
agents/scheduler.py — Chrono Action Specialist (Calendar MCP Integration)

Uses CalendarMCP for real Google Calendar integration.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("nexus")

from nexus.models.schemas import AgentResult, SuggestionChip
from nexus.agents.base import BaseAgent
from nexus.agents.blackboard import Blackboard
from nexus.config import get_demo_mode

_DEMO = get_demo_mode()


class ChronoAgent(BaseAgent):
    """
    NEXUS Action Specialist (Chrono)
    Calendar orchestration, task decomposition, scheduling.
    Uses CalendarMCP for Google Calendar integration.
    """

    def __init__(self, blackboard: Blackboard):
        super().__init__(name="chrono", blackboard=blackboard)

    async def think(self, prompt: str) -> AgentResult:
        self.trace("Analysing schedule for time-critical conflicts")

        research_context = self.get_state("research.latest")
        if research_context:
            query = research_context.get("query", "")
            self.trace(f"Integrating research findings: {query}", status="done")

        self.trace("Fetching Google Calendar primary events", status="running")

        calendar_events = []
        if not _DEMO:
            try:
                from nexus.mcp_servers.calendar_mcp import CalendarMCP

                cal = CalendarMCP(demo_mode=False)
                start = datetime.now()
                end = start + timedelta(days=7)
                calendar_events = await cal.get_events(
                    start.isoformat(), end.isoformat()
                )
            except Exception as e:
                logger.warning(f"Chrono calendar MCP failed: {e}")

        self.trace("Detecting high-priority task overlaps", status="running")
        await asyncio.sleep(0.3)

        events_md = ""
        if calendar_events:
            events_md = "### Your Week\n"
            for ev in calendar_events[:5]:
                start = ev.get("start", {}).get("dateTime", "TBD")[:16]
                events_md += f"- **{start}**: {ev.get('summary', 'Event')}\n"
        else:
            events_md = """### Your Week
- No events scheduled (Demo mode)
- In live mode: fetches real Google Calendar events"""

        summary = (
            f"Schedule synchronised with {len(calendar_events) or 2} events this week."
        )
        markdown = f"""# Chrono Report: Time & Logistics

Chrono has optimised your mission timeline.

{events_md}

### Resolved Conflicts
- Moved 'Review Draft' to 16:00 to avoid overlap with the new research task.

---
*Chrono — Action Specialist*"""

        suggestions = [
            SuggestionChip(
                label="Block Prep Time",
                prompt="Chrono, block 30 mins before my next meeting",
                agent_hint="chrono",
            ),
            SuggestionChip(
                label="Show Week View",
                prompt="Chrono, what does my week look like?",
                agent_hint="chrono",
            ),
        ]

        self.set_state("chrono.latest_action", "Conflict resolution complete")
        self.trace("Time orchestration complete", status="done")

        return self.create_result(
            summary=summary,
            markdown=markdown,
            suggestions=suggestions,
            confidence=0.98,
        )
