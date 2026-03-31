"""
agents/__init__.py — NEXUS Agents Package
"""
from __future__ import annotations

from nexus.agents.orchestrator import SwarmEngine, create_orchestrator
from nexus.agents.blackboard import Blackboard
from nexus.agents.base import BaseAgent
from nexus.agents.research import AtlasAgent
from nexus.agents.scheduler import ChronoAgent
from nexus.agents.notes import SageAgent
from nexus.agents.memory import MnemoAgent
from nexus.agents.goal_strategist import GoalStrategistAgent
from nexus.agents.task_manager import TasksAgent
from nexus.agents.briefing import BriefingAgent
from nexus.agents.analytics_agent import AnalyticsAgent
from nexus.agents.workflow import WorkflowAgent

__all__ = [
    "SwarmEngine", "create_orchestrator",
    "Blackboard", "BaseAgent",
    "AtlasAgent", "ChronoAgent", "SageAgent", "MnemoAgent",
    "GoalStrategistAgent", "TasksAgent", "BriefingAgent",
    "AnalyticsAgent", "WorkflowAgent",
]
