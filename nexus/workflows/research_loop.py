"""
research_loop.py — Research Loop Workflow

SequentialAgent + LoopAgent workflow:
1. SequentialAgent: Research → search Tavily + Wikipedia (output_key: "raw_research")
2. LoopAgent (pure Gemini, no MCP):
   - Reviewer scores quality 1-10
   - If < 7 AND iterations < 3: loop
   - If >= 7 OR max reached: escalate=True
3. Notes → structure notes → save to Firestore
4. Memory → save topic interest
"""

import logging
from typing import Any

logger = logging.getLogger("nexus")
from nexus.config import get_demo_mode
DEMO_MODE = get_demo_mode()


class ResearchLoopWorkflow:
    """Workflow for iterative research with quality scoring."""

    def __init__(self, demo_mode: bool = DEMO_MODE):
        self.demo_mode = demo_mode or DEMO_MODE
        self.max_iterations = 3

    async def run(self, prompt: str, user_id: str, session_id: str) -> dict[str, Any]:
        """Execute the research loop workflow."""
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
            "action": "Initial research",
            "output_key": "raw_research",
            "result": "Found 15 sources from search and Wikipedia",
        }
        steps.append(step1)

        loop_iterations = []
        for i in range(2):
            score = 8 if i == 1 else 5
            loop_iterations.append(
                {
                    "iteration": i + 1,
                    "quality_score": score,
                    "action": f"Reviewer scores quality {score}/10",
                    "decision": "loop" if score < 7 and i < 2 else "escalate",
                }
            )

        step2 = {
            "step": 2,
            "agent": "reviewer",
            "action": "Quality scoring loop",
            "loop_iterations": loop_iterations,
            "final_score": 8,
            "escalated": True,
        }
        steps.append(step2)

        step3 = {
            "step": 3,
            "agent": "notes",
            "action": "Structuring and saving notes",
            "result": "Saved structured notes to Firestore",
        }
        steps.append(step3)

        step4 = {
            "step": 4,
            "agent": "memory",
            "action": "Saving topic interest",
            "result": "Saved to long-term memory",
        }
        steps.append(step4)

        return {
            "workflow_type": "research_loop",
            "prompt": prompt,
            "user_id": user_id,
            "session_id": session_id,
            "steps": steps,
            "total_steps": 4,
            "agents_used": ["research", "reviewer", "notes", "memory"],
            "loop_iterations": len(loop_iterations),
            "final_quality_score": 8,
            "from_demo_mode": True,
        }

    async def _live_run(
        self, prompt: str, user_id: str, session_id: str
    ) -> dict[str, Any]:
        """Live mode: use real ADK agents. Falls back to demo if not configured."""
        logger.warning("Live mode not fully configured, falling back to demo mode")
        return await self._demo_run(prompt, user_id, session_id)


async def run_research_loop(
    prompt: str, user_id: str, session_id: str
) -> dict[str, Any]:
    """Convenience function to run research loop workflow."""
    workflow = ResearchLoopWorkflow(demo_mode=DEMO_MODE)
    return await workflow.run(prompt, user_id, session_id)
