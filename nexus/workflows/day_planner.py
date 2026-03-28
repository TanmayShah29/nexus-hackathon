"""
day_planner.py — Day Planner Workflow

ParallelAgent + SequentialAgent workflow:
1. ParallelAgent:
   - Dash → pending tasks (output_key: "pending_tasks")
   - Chrono → calendar (output_key: "todays_calendar")
   - Flux → weather (output_key: "weather_data")
2. SequentialAgent:
   - Step 2: Flux → synthesise (reads all 3 outputs, output_key: "briefing_plan")
   - Step 3: Chrono → time-blocks (reads {briefing_plan?})
   - Step 4: Mnemo → save prefs
"""

import os
import asyncio
from typing import Any

DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"


class DayPlannerWorkflow:
    """Workflow for daily planning."""

    def __init__(self, demo_mode: bool = DEMO_MODE):
        self.demo_mode = demo_mode or DEMO_MODE

    async def run(self, prompt: str, user_id: str, session_id: str) -> dict[str, Any]:
        """Execute the day planner workflow."""
        if self.demo_mode:
            return await self._demo_run(prompt, user_id, session_id)
        return await self._live_run(prompt, user_id, session_id)

    async def _demo_run(
        self, prompt: str, user_id: str, session_id: str
    ) -> dict[str, Any]:
        """Demo mode: return mock workflow result."""
        from mcp_servers import WeatherMCP

        weather = WeatherMCP(demo_mode=True)
        weather_data = await weather.get_current("Mumbai")

        steps = []

        step1a = {
            "step": 1,
            "agent": "dash",
            "action": "Getting pending tasks",
            "output_key": "pending_tasks",
            "result": "Found 5 pending tasks",
        }
        steps.append(step1a)

        step1b = {
            "step": 1,
            "agent": "chrono",
            "action": "Reading calendar",
            "output_key": "todays_calendar",
            "result": "3 events today",
        }
        steps.append(step1b)

        step1c = {
            "step": 1,
            "agent": "flux",
            "action": "Getting weather",
            "output_key": "weather_data",
            "result": f"{weather_data['description']}, {weather_data['temperature']}°C",
        }
        steps.append(step1c)

        step2 = {
            "step": 2,
            "agent": "flux",
            "action": "Synthesising briefing",
            "input_keys": ["pending_tasks", "todays_calendar", "weather_data"],
            "output_key": "briefing_plan",
            "result": "Created daily briefing",
        }
        steps.append(step2)

        step3 = {
            "step": 3,
            "agent": "chrono",
            "action": "Time-blocking",
            "input_key": "briefing_plan",
            "result": "Created 3 time blocks",
        }
        steps.append(step3)

        step4 = {
            "step": 4,
            "agent": "mnemo",
            "action": "Saving preferences",
            "result": "Saved user preferences",
        }
        steps.append(step4)

        return {
            "workflow_type": "day_planner",
            "prompt": prompt,
            "user_id": user_id,
            "session_id": session_id,
            "steps": steps,
            "total_steps": 4,
            "agents_used": ["dash", "chrono", "flux", "mnemo"],
            "from_demo_mode": True,
        }

    async def _live_run(
        self, prompt: str, user_id: str, session_id: str
    ) -> dict[str, Any]:
        """Live mode: use real ADK agents."""
        raise NotImplementedError("Live mode requires ADK setup")


async def run_day_planner(prompt: str, user_id: str, session_id: str) -> dict[str, Any]:
    """Convenience function to run day planner workflow."""
    workflow = DayPlannerWorkflow(demo_mode=DEMO_MODE)
    return await workflow.run(prompt, user_id, session_id)
