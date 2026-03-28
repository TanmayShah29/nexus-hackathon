"""
exam_prep.py — Exam Preparation Workflow

SequentialAgent + ParallelAgent workflow:
1. Atlas → research topics (output_key: "exam_topics")
2. Sage → structure notes (reads {exam_topics?}, output_key: "exam_notes")
3. ParallelAgent:
   - Chrono → block time slots (output_key: "chrono_output")
   - Dash → create checklist (output_key: "dash_output")
4. Mnemo → save to memory
"""

import os
import asyncio
from typing import Any

DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"


class ExamPrepWorkflow:
    """Workflow for exam preparation."""

    def __init__(self, demo_mode: bool = DEMO_MODE):
        self.demo_mode = demo_mode or DEMO_MODE

    async def run(self, prompt: str, user_id: str, session_id: str) -> dict[str, Any]:
        """Execute the exam prep workflow."""
        if self.demo_mode:
            return await self._demo_run(prompt, user_id, session_id)
        return await self._live_run(prompt, user_id, session_id)

    async def _demo_run(
        self, prompt: str, user_id: str, session_id: str
    ) -> dict[str, Any]:
        """Demo mode: return mock workflow result."""
        from mcp_servers import SearchMCP, WikipediaMCP

        steps = []

        step1 = {
            "step": 1,
            "agent": "atlas",
            "action": "Researching exam topics",
            "output_key": "exam_topics",
            "result": "Found 14 topics: OOP, Data Structures, Algorithms, Async, Decorators, etc.",
        }
        steps.append(step1)

        step2 = {
            "step": 2,
            "agent": "sage",
            "action": "Structuring notes",
            "input_key": "exam_topics",
            "output_key": "exam_notes",
            "result": "Created structured notes with 14 sections",
        }
        steps.append(step2)

        step3a = {
            "step": 3,
            "agent": "chrono",
            "action": "Blocking time slots",
            "output_key": "chrono_output",
            "result": "Blocked 2 hours tomorrow 2-4 PM",
        }
        steps.append(step3a)

        step3b = {
            "step": 3,
            "agent": "dash",
            "action": "Creating checklist",
            "output_key": "dash_output",
            "result": "Created checklist with 20 items",
        }
        steps.append(step3b)

        step4 = {
            "step": 4,
            "agent": "mnemo",
            "action": "Saving to memory",
            "input_keys": ["exam_topics", "exam_notes", "chrono_output", "dash_output"],
            "result": "Saved all outputs to memory",
        }
        steps.append(step4)

        return {
            "workflow_type": "exam_prep",
            "prompt": prompt,
            "user_id": user_id,
            "session_id": session_id,
            "steps": steps,
            "total_steps": 4,
            "agents_used": ["atlas", "sage", "chrono", "dash", "mnemo"],
            "from_demo_mode": True,
        }

    async def _live_run(
        self, prompt: str, user_id: str, session_id: str
    ) -> dict[str, Any]:
        """Live mode: use real ADK agents."""
        raise NotImplementedError("Live mode requires ADK setup")


async def run_exam_prep(prompt: str, user_id: str, session_id: str) -> dict[str, Any]:
    """Convenience function to run exam prep workflow."""
    workflow = ExamPrepWorkflow(demo_mode=DEMO_MODE)
    return await workflow.run(prompt, user_id, session_id)
