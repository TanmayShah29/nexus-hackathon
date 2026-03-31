"""
agents/orchestrator.py — NEXUS SwarmEngine

Phase-based parallel specialist execution via asyncio.gather.
LLM (Gemini) generates the plan; agents actually execute.
"""
from __future__ import annotations

import asyncio
import time
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nexus")

from nexus.models.schemas import AgentResult, SuggestionChip
from nexus.agents.blackboard import Blackboard


class SwarmEngine:
    """Parallel specialist execution engine."""

    def __init__(self, blackboard: Blackboard):
        self.blackboard = blackboard
        self.session_id = blackboard.session_id

        try:
            from nexus.memory.supabase_client import get_supabase_client
            sb = get_supabase_client()
            if sb.is_active():
                sb.ensure_thread_exists(self.session_id)
        except Exception:
            pass

    # ── Agent factory ──────────────────────────────────────────

    def _make_agent(self, name: str):
        """Lazy agent instantiation. All use BaseAgent(name, blackboard)."""
        from nexus.agents.research import AtlasAgent
        from nexus.agents.scheduler import ChronoAgent
        from nexus.agents.notes import SageAgent
        from nexus.agents.memory import MnemoAgent
        from nexus.agents.goal_strategist import GoalStrategistAgent
        from nexus.agents.task_manager import TasksAgent
        from nexus.agents.briefing import BriefingAgent
        from nexus.agents.analytics_agent import AnalyticsAgent
        from nexus.agents.workflow import WorkflowAgent

        registry: Dict[str, Any] = {
            # Primary names
            "atlas": AtlasAgent,
            "chrono": ChronoAgent,
            "sage": SageAgent,
            "mnemo": MnemoAgent,
            "goals": GoalStrategistAgent,
            "tasks": TasksAgent,
            "briefing": BriefingAgent,
            "analytics": AnalyticsAgent,
            "workflow": WorkflowAgent,
            # Aliases the LLM sometimes emits
            "research": AtlasAgent,
            "scheduler": ChronoAgent,
            "memory": MnemoAgent,
            "notes": SageAgent,
            "task_manager": TasksAgent,
        }
        cls = registry.get(name.lower())
        if cls is None:
            logger.warning(f"SwarmEngine: unknown agent '{name}', skipping.")
            return None
        return cls(blackboard=self.blackboard)

    # ── Planning ───────────────────────────────────────────────

    async def generate_strategy(self, prompt: str) -> List[List[Dict[str, Any]]]:
        """Use Gemini to build a phase plan; fall back to sensible default."""
        from nexus.agents.gemini_client import generate_plan
        try:
            ctx = self.blackboard.get_prompt_context()
            plan = await generate_plan(prompt, blackboard_context=ctx)
            if plan:
                logger.info(f"SwarmEngine | plan={plan}")
                return plan
        except Exception as e:
            logger.warning(f"SwarmEngine | plan generation failed: {e}")

        # Default two-phase plan
        return [
            [
                {"agent": "atlas",  "goal": f"Research: {prompt}"},
                {"agent": "mnemo",  "goal": f"Recall relevant context for: {prompt}"},
            ],
            [
                {"agent": "sage",   "goal": f"Structure findings for: {prompt}"},
                {"agent": "chrono", "goal": "Update tasks and schedule if relevant"},
            ],
        ]

    # ── Execution ─────────────────────────────────────────────

    async def execute_swarm(
        self, prompt: str, strategy: List[List[Dict[str, Any]]]
    ) -> AgentResult:
        """Run phases sequentially; agents within each phase run in parallel."""
        start = time.time()
        last_result: Optional[AgentResult] = None

        for i, phase in enumerate(strategy):
            phase_num = i + 1
            agent_names = [s["agent"] for s in phase]
            logger.info(f"SwarmEngine | Phase {phase_num}: {agent_names}")

            self.blackboard.history.append({
                "timestamp": time.time(),
                "agent": "orchestrator",
                "action": f"Phase {phase_num}: {', '.join(agent_names)}",
                "status": "running",
            })

            coros = []
            for step in phase:
                agent = self._make_agent(step["agent"])
                if agent is not None:
                    self.blackboard.set(f"swarm.active.{step['agent']}", True)
                    coros.append(agent.think(step.get("goal", prompt)))

            if coros:
                try:
                    results = await asyncio.gather(*coros, return_exceptions=True)
                    for step, result in zip(phase, results):
                        self.blackboard.set(f"swarm.active.{step['agent']}", False)
                        if isinstance(result, Exception):
                            logger.error(f"SwarmEngine | {step['agent']} error: {result}")
                        elif isinstance(result, AgentResult):
                            last_result = result
                except asyncio.CancelledError:
                    for step in phase:
                        self.blackboard.set(f"swarm.active.{step['agent']}", False)
                    await self.blackboard.save()
                    raise

            await self.blackboard.save()

        duration_ms = int((time.time() - start) * 1000)
        agents_run = [s["agent"] for phase in strategy for s in phase]

        if last_result:
            last_result.metrics.update({"duration_ms": duration_ms, "phases": len(strategy)})
            return last_result

        return AgentResult(
            agent="orchestrator",
            session_id=self.session_id,
            summary=f"Swarm completed {len(strategy)} phase(s) in {duration_ms}ms.",
            markdown_content=f"Ran **{len(strategy)} phase(s)** with specialists: {', '.join(agents_run)}.",
            suggestions=[
                SuggestionChip(label="Review memories", prompt="What did Mnemo find?"),
                SuggestionChip(label="Check schedule", prompt="Show my updated calendar"),
            ],
            metrics={"duration_ms": duration_ms, "phases": len(strategy)},
            confidence=0.85,
        )

    # ── Public API ─────────────────────────────────────────────

    async def plan(self, prompt: str) -> List[List[Dict[str, Any]]]:
        return await self.generate_strategy(prompt)

    async def run(self, prompt: str, plan: Optional[List[List[Dict[str, Any]]]] = None) -> dict:
        strategy = plan or await self.generate_strategy(prompt)
        result = await self.execute_swarm(prompt, strategy)
        return result.model_dump()


def create_orchestrator(blackboard: Blackboard) -> SwarmEngine:
    return SwarmEngine(blackboard)
