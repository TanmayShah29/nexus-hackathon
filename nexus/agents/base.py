"""
base.py — NEXUS BaseAgent (Fixed)

Single unified BaseAgent used by ALL specialists.
Takes a Blackboard, emits traces, returns AgentResult.
"""
from __future__ import annotations

import abc
import time
from typing import Any, Dict, List, Optional

import logging
logger = logging.getLogger("nexus")

from nexus.models.schemas import (
    AgentName, AgentResult, AgentIdentity, TraceStatus,
    SuggestionChip, AGENT_IDENTITY_MAP,
)
from nexus.agents.blackboard import Blackboard


class BaseAgent(abc.ABC):
    """
    Foundation for all NEXUS specialists.
    Provides unified tracing, blackboard I/O, and structured output.
    """

    def __init__(self, name: AgentName, blackboard: Blackboard):
        # FIX: Safely fall back for agents not in AGENT_IDENTITY_MAP
        self.identity: Optional[AgentIdentity] = AGENT_IDENTITY_MAP.get(name)
        self.name = name
        self.blackboard = blackboard
        self.session_id = blackboard.session_id

    def trace(
        self,
        action: str,
        status: TraceStatus = "running",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Emit a trace event — updates the Blackboard history and Supabase."""
        trace_data = {
            "timestamp": time.time(),
            "agent": self.name,
            "action": action,
            "status": status,
            "metadata": metadata or {},
        }

        # Supabase persistence (non-fatal)
        try:
            from nexus.memory.supabase_client import get_supabase_client
            sb = get_supabase_client()
            if sb.is_active():
                sb.log_trace(
                    thread_id=self.session_id,
                    agent_id=self.name,
                    status=status,
                    message=action,
                )
        except Exception as e:
            logger.warning(f"Trace Supabase log failed (non-fatal): {e}")

        display = self.identity.display_name if self.identity else self.name.title()
        logger.info(f"Trace | {display} | {action} [{status}]")
        self.blackboard.history.append(trace_data)

    @abc.abstractmethod
    async def think(self, prompt: str) -> AgentResult:
        """Specialist reasoning — implemented by every subclass."""
        pass

    def create_result(
        self,
        summary: str,
        markdown: str = "",
        suggestions: Optional[List[SuggestionChip]] = None,
        confidence: float = 1.0,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """Standardised output factory."""
        return AgentResult(
            agent=self.name,
            session_id=self.session_id,
            summary=summary,
            markdown_content=markdown,
            suggestions=suggestions or [],
            confidence=confidence,
            metrics=metrics or {},
        )

    def get_state(self, key: str, default: Any = None) -> Any:
        return self.blackboard.get(key, default)

    def set_state(self, key: str, value: Any):
        self.blackboard.set(key, value, agent_id=self.name)
