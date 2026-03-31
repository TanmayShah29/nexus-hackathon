"""
exam_prep.py — Exam Preparation Workflow

SequentialAgent + ParallelAgent workflow:
1. Research → research topics (output_key: "exam_topics")
2. Notes → structure notes (reads {exam_topics?}, output_key: "exam_notes")
3. ParallelAgent:
   - Scheduler → block time slots (output_key: "scheduler_output")
   - Tasks → create checklist (output_key: "tasks_output")
4. Memory → save to memory
"""

import logging
from typing import Any

logger = logging.getLogger("nexus")
from nexus.config import get_demo_mode
DEMO_MODE = get_demo_mode()


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

        steps = []

        step1 = {
            "step": 1,
            "agent": "research",
            "action": "Researching exam topics",
            "output_key": "exam_topics",
            "result": "Found 14 topics: OOP, Data Structures, Algorithms, Async, Decorators, etc.",
        }
        steps.append(step1)

        step2 = {
            "step": 2,
            "agent": "notes",
            "action": "Structuring notes",
            "input_key": "exam_topics",
            "output_key": "exam_notes",
            "result": "Created structured notes with 14 sections",
        }
        steps.append(step2)

        step3a = {
            "step": 3,
            "agent": "scheduler",
            "action": "Blocking time slots",
            "output_key": "scheduler_output",
            "result": "Blocked 2 hours tomorrow 2-4 PM",
        }
        steps.append(step3a)

        step3b = {
            "step": 3,
            "agent": "tasks",
            "action": "Creating checklist",
            "output_key": "tasks_output",
            "result": "Created checklist with 20 items",
        }
        steps.append(step3b)

        step4 = {
            "step": 4,
            "agent": "memory",
            "action": "Saving to memory",
            "input_keys": [
                "exam_topics",
                "exam_notes",
                "scheduler_output",
                "tasks_output",
            ],
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
            "agents_used": ["research", "notes", "scheduler", "tasks", "memory"],
            "from_demo_mode": True,
        }

    async def _live_run(
        self, prompt: str, user_id: str, session_id: str
    ) -> dict[str, Any]:
        """Live mode: use real ADK agents. Falls back to demo if not configured."""
        logger.warning("Live mode not fully configured, falling back to demo mode")
        return await self._demo_run(prompt, user_id, session_id)


async def run_exam_prep(prompt: str, user_id: str, session_id: str) -> dict[str, Any]:
    """Convenience function to run exam prep workflow."""
    workflow = ExamPrepWorkflow(demo_mode=DEMO_MODE)
    return await workflow.run(prompt, user_id, session_id)
