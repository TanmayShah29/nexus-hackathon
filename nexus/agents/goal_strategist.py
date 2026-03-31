"""
goal_strategist.py — Goals Agent
"""

import logging

logger = logging.getLogger("nexus")

from nexus.models.schemas import AgentResult, SuggestionChip
from nexus.agents.base import BaseAgent
from nexus.agents.blackboard import Blackboard


class GoalStrategistAgent(BaseAgent):
    """
    Goals agent - 90-day roadmapping.
    Inherits from BaseAgent for unified tracing and results.
    """

    def __init__(self, blackboard: Blackboard):
        super().__init__(name="goals", blackboard=blackboard)

    async def think(self, prompt: str) -> AgentResult:
        """Execute the goal roadmapping logic."""
        self.trace("Decomposing objectives into milestones", status="running")

        goal = (
            prompt.lower().replace("learn", "").replace("become", "").strip()
            or "your objective"
        )

        self.trace("Roadmap generated", status="done")

        markdown = f"""# {goal.title()} Strategy

## Phase 1: Foundation (30 Days)
- Master core concepts
- Complete initial certifications

## Phase 2: Execution (60 Days)
- Build 3 portfolio projects
- Join relevant communities

## Phase 3: Mastery (90 Days)
- Apply for advanced opportunities
- Final project completion"""

        return self.create_result(
            summary=f"Created a 90-day strategy for {goal}.",
            markdown=markdown,
            suggestions=[
                SuggestionChip(
                    label="Add first milestone",
                    prompt=f"Create tasks for Phase 1 of {goal}",
                    agent_hint="tasks",
                )
            ],
        )
