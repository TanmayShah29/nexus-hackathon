"""
task_manager.py — Tasks Agent
"""

import asyncio
import uuid
from typing import List
import logging

logger = logging.getLogger("nexus")

from nexus.models.schemas import AgentResult, SuggestionChip
from nexus.agents.base import BaseAgent
from nexus.agents.blackboard import Blackboard


class TasksAgent(BaseAgent):
    """
    Tasks agent - manages to-do list and task execution.
    Inherits from BaseAgent for unified tracing and results.
    """

    def __init__(self, blackboard: Blackboard):
        super().__init__(name="tasks", blackboard=blackboard)

    async def think(self, prompt: str) -> AgentResult:
        """Execute the task management logic with Blackboard awareness."""
        prompt_lower = prompt.lower()

        self.trace("Analyzing task intent")

        if "list" in prompt_lower or "show" in prompt_lower:
            return await self._list_tasks()

        self.trace("Extracting and creating tasks", status="running")

        tasks = self._extract_tasks(prompt)

        for t in tasks:
            task_id = f"task_{uuid.uuid4().hex[:8]}"
            self.set_state(f"tasks.{task_id}", {"title": t, "status": "pending"})
            await asyncio.sleep(0.1)

        self.trace(f"Created {len(tasks)} tasks", status="done")

        summary = f"Added {len(tasks)} tasks to your list."
        markdown = "# Tasks Added ✓\n\n" + "\n".join([f"- {t}" for t in tasks])

        return self.create_result(
            summary=summary,
            markdown=markdown,
            suggestions=[
                SuggestionChip(
                    label="Schedule these",
                    prompt="Schedule time for my new tasks",
                    agent_hint="chrono",
                ),
                SuggestionChip(
                    label="Show all tasks",
                    prompt="What are my pending tasks?",
                    agent_hint="tasks",
                ),
            ],
        )

    async def _list_tasks(self) -> AgentResult:
        self.trace("Fetching task list", status="running")

        all_tasks = []
        for key, value in self.blackboard.data.get("tasks", {}).items():
            all_tasks.append(value)

        if not all_tasks:
            all_tasks = [{"title": "No tasks yet — add some!", "priority": "info"}]

        self.trace(f"Retrieved {len(all_tasks)} task(s)", status="done")

        markdown = "# Your Pending Tasks\n\n" + "\n".join(
            [
                f"- **{t.get('title', 'Task')}** [{t.get('priority', 'normal').upper()}]"
                for t in all_tasks
            ]
        )

        return self.create_result(
            summary=f"Found {len(all_tasks)} task(s).",
            markdown=markdown,
        )

    def _extract_tasks(self, prompt: str) -> List[str]:
        clean = (
            prompt.lower()
            .replace("add", "")
            .replace("task", "")
            .replace("todo", "")
            .strip()
        )
        if "," in clean:
            return [t.strip() for t in clean.split(",")]
        return [clean] if clean else ["New task"]
