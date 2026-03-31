"""
test_orchestrator.py — Tests for NEXUS Core Orchestrator
"""

import pytest
from nexus.agents.orchestrator import SwarmEngine
from nexus.agents.blackboard import Blackboard


class TestSwarmEngine:
    @pytest.fixture
    def blackboard(self):
        return Blackboard(session_id="test-session", user_id="test-user")

    def test_initialization(self, blackboard):
        engine = SwarmEngine(blackboard)
        assert engine.session_id == "test-session"
        assert engine.blackboard is not None

    def test_make_agent_atlas(self, blackboard):
        engine = SwarmEngine(blackboard)
        agent = engine._make_agent("atlas")
        assert agent is not None
        assert agent.name == "atlas"

    def test_make_agent_chrono(self, blackboard):
        engine = SwarmEngine(blackboard)
        agent = engine._make_agent("chrono")
        assert agent is not None
        assert agent.name == "chrono"

    def test_make_agent_invalid(self, blackboard):
        engine = SwarmEngine(blackboard)
        agent = engine._make_agent("invalid_agent")
        assert agent is None


class TestCreateOrchestrator:
    def test_create_with_blackboard(self):
        bb = Blackboard(session_id="my-session", user_id="my-user")
        orch = SwarmEngine(bb)
        assert orch.session_id == "my-session"
