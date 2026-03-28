"""
orchestrator.py — NEXUS Core Orchestrator

The main orchestrator that routes intents to specialist agents.
In demo mode, returns structured mock responses.
"""

import os
import asyncio
from typing import Any, Optional

DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"


class NEXUSOrchestrator:
    """
    NEXUS Core — the main orchestrator agent.
    """

    def __init__(self, session_id: str = "default", user_id: str = "default"):
        self.session_id = session_id
        self.user_id = user_id
        self.demo_mode = DEMO_MODE

    async def run(self, prompt: str) -> dict[str, Any]:
        """Main entry point. Returns a dict with agent results."""
        if self.demo_mode:
            return await self._demo_route(prompt)
        return await self._live_route(prompt)

    async def _demo_route(self, prompt: str) -> dict[str, Any]:
        """Demo mode: route to appropriate agent."""
        from mcp_servers import SearchMCP, WeatherMCP, WikipediaMCP

        prompt_lower = prompt.lower()

        if any(
            kw in prompt_lower
            for kw in ["search", "research", "what is", "learn", "explain"]
        ):
            return await self._demo_atlas(prompt)
        elif any(
            kw in prompt_lower
            for kw in ["schedule", "calendar", "time", "meeting", "book"]
        ):
            return await self._demo_chrono(prompt)
        elif any(kw in prompt_lower for kw in ["note", "save", "write", "document"]):
            return await self._demo_sage(prompt)
        elif any(
            kw in prompt_lower for kw in ["remember", "memory", "past", "previous"]
        ):
            return await self._demo_mnemo(prompt)
        elif any(kw in prompt_lower for kw in ["brief", "summary", "day", "morning"]):
            return await self._demo_flux(prompt)
        elif any(kw in prompt_lower for kw in ["task", "todo", "do", "action"]):
            return await self._demo_dash(prompt)
        else:
            return await self._demo_atlas(prompt)

    async def _demo_atlas(self, prompt: str) -> dict[str, Any]:
        """Atlas: Research agent."""
        from mcp_servers import SearchMCP, WikipediaMCP

        search = SearchMCP(demo_mode=True)
        wiki = WikipediaMCP(demo_mode=True)

        query = prompt.replace("what is", "").replace("explain", "").strip()

        search_results = await search.search(query, 3)
        wiki_result = await wiki.search(query)

        tool_calls = [
            {
                "tool": "tavily_search",
                "tool_display_name": "Tavily Search",
                "status": "done",
                "action": f"Searching for '{query}'",
                "detail": f"Found {len(search_results)} results",
            },
            {
                "tool": "wikipedia",
                "tool_display_name": "Wikipedia",
                "status": "done",
                "action": "Fetching Wikipedia summary",
                "detail": wiki_result.get("extract", "")[:200],
            },
        ]

        summary = f"Here's what I found about '{query}':\n\n{wiki_result.get('extract', '')[:300]}..."

        return {
            "agent": "atlas",
            "agent_display_name": "Atlas",
            "session_id": self.session_id,
            "workflow_type": "simple",
            "summary": summary,
            "full_response": f"# Research Results\n\n{wiki_result.get('extract', '')}\n\n## Sources\n"
            + "\n".join([f"- [{r['title']}]({r['url']})" for r in search_results]),
            "tool_calls": tool_calls,
            "suggestions": [
                {
                    "label": "Save to notes",
                    "prompt": f"Save this research about {query}",
                    "agent_hint": "sage",
                },
            ],
            "confidence": 0.9,
            "from_demo_mode": True,
        }

    async def _demo_chrono(self, prompt: str) -> dict[str, Any]:
        """Chrono: Scheduling agent."""
        from mcp_servers import WeatherMCP

        weather = WeatherMCP(demo_mode=True)
        weather_data = await weather.get_current("Mumbai")

        tool_calls = [
            {
                "tool": "google_calendar",
                "tool_display_name": "Google Calendar",
                "status": "done",
                "action": "Checking today's calendar",
                "detail": "Found 3 events today",
            },
            {
                "tool": "openweathermap",
                "tool_display_name": "Weather",
                "status": "done",
                "action": "Checking weather",
                "detail": f"{weather_data['description']}, {weather_data['temperature']}°C",
            },
        ]

        return {
            "agent": "chrono",
            "agent_display_name": "Chrono",
            "session_id": self.session_id,
            "workflow_type": "simple",
            "summary": "Your schedule for today:\n\n• 9:00 AM - Team Standup\n• 2:00 PM - Python Interview Prep\n\nWeather: Clear sky, 28°C",
            "full_response": "# Today's Schedule\n\n| Time | Event |\n|------|-------|\n| 9:00 AM | Team Standup |\n| 2:00 PM | Python Interview Prep |\n\n## Weather\nClear sky, 28°C",
            "tool_calls": tool_calls,
            "suggestions": [
                {
                    "label": "Block study time",
                    "prompt": "Block 2 hours for interview prep",
                    "agent_hint": "chrono",
                }
            ],
            "confidence": 0.9,
            "from_demo_mode": True,
        }

    async def _demo_sage(self, prompt: str) -> dict[str, Any]:
        """Sage: Notes agent."""
        return {
            "agent": "sage",
            "agent_display_name": "Sage",
            "session_id": self.session_id,
            "workflow_type": "simple",
            "summary": "I've saved your notes.",
            "full_response": "Notes saved successfully.",
            "tool_calls": [
                {
                    "tool": "firestore",
                    "tool_display_name": "Firestore",
                    "status": "done",
                    "action": "Writing to Firestore",
                    "detail": "Document saved",
                }
            ],
            "suggestions": [],
            "confidence": 0.9,
            "from_demo_mode": True,
        }

    async def _demo_mnemo(self, prompt: str) -> dict[str, Any]:
        """Mnemo: Memory agent."""
        return {
            "agent": "mnemo",
            "agent_display_name": "Mnemo",
            "session_id": self.session_id,
            "workflow_type": "simple",
            "summary": "I found your previous sessions:\n\n• Last week: You prepared for a system design interview\n• Yesterday: You asked about Python decorators",
            "full_response": "# Memory\n\n## Recent Sessions\n- Last week: System design interview prep\n- Yesterday: Python decorators question",
            "tool_calls": [],
            "suggestions": [],
            "confidence": 0.9,
            "from_demo_mode": True,
        }

    async def _demo_flux(self, prompt: str) -> dict[str, Any]:
        """Flux: Briefing agent."""
        from mcp_servers import WeatherMCP

        weather = WeatherMCP(demo_mode=True)
        weather_data = await weather.get_current("Mumbai")

        return {
            "agent": "flux",
            "agent_display_name": "Flux",
            "session_id": self.session_id,
            "workflow_type": "simple",
            "summary": f"# Good Morning!\n\nHere's your briefing:\n\n## Weather\n{weather_data['description']}, {weather_data['temperature']}°C\n\n## Tasks\n3 tasks pending\n\n## Focus\nYour Python interview is today at 2 PM!",
            "full_response": "# Daily Briefing\n\n## Weather\nClear sky, 28°C\n\n## Pending Tasks\n- Team Standup (9:00 AM)\n- Python Interview Prep (2:00 PM)",
            "tool_calls": [
                {
                    "tool": "openweathermap",
                    "tool_display_name": "Weather",
                    "status": "done",
                    "action": "Getting weather",
                    "detail": f"{weather_data['description']}, {weather_data['temperature']}°C",
                }
            ],
            "suggestions": [
                {
                    "label": "Start interview prep",
                    "prompt": "Start my interview prep session",
                    "agent_hint": "atlas",
                }
            ],
            "confidence": 0.9,
            "from_demo_mode": True,
        }

    async def _demo_dash(self, prompt: str) -> dict[str, Any]:
        """Dash: Tasks agent."""
        return {
            "agent": "dash",
            "agent_display_name": "Dash",
            "session_id": self.session_id,
            "workflow_type": "simple",
            "summary": "I've added this to your tasks:\n\n1. Review Python concepts\n2. Practice system design\n3. Prepare questions for interviewer",
            "full_response": "# Tasks Added\n\n1. Review Python concepts\n2. Practice system design\n3. Prepare questions for interviewer",
            "tool_calls": [],
            "suggestions": [],
            "confidence": 0.9,
            "from_demo_mode": True,
        }

    async def _live_route(self, prompt: str) -> dict[str, Any]:
        """Live mode: use real agents with ADK."""
        raise NotImplementedError("Live mode not implemented - requires ADK setup")


def create_orchestrator(
    session_id: str = "default", user_id: str = "default"
) -> NEXUSOrchestrator:
    """Factory function to create an orchestrator."""
    return NEXUSOrchestrator(session_id=session_id, user_id=user_id)
