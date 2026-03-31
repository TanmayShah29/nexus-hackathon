"""tests/test_blackboard.py — Blackboard unit tests"""
import pytest
from nexus.agents.blackboard import Blackboard


class TestBlackboard:
    @pytest.fixture
    def bb(self):
        return Blackboard(session_id="test-session", user_id="test-user")

    def test_initialization(self, bb):
        assert bb.session_id == "test-session"
        assert bb.user_id == "test-user"
        assert bb.data == {}

    def test_set_and_get(self, bb):
        bb.set("test_key", "test_value", "agent1")
        assert bb.get("test_key") == "test_value"

    def test_get_default(self, bb):
        assert bb.get("nonexistent", "default") == "default"

    def test_nested_keys(self, bb):
        bb.set("parent.child", "value", "agent1")
        assert bb.get("parent.child") == "value"
        assert bb.data["parent"]["child"] == "value"

    def test_history_recorded(self, bb):
        bb.set("k", "v", "agent_x")
        assert any(e["agent"] == "agent_x" for e in bb.history)

    def test_model_dump(self, bb):
        bb.set("k", "v", "agent1")
        d = bb.model_dump()
        assert d["session_id"] == "test-session"
        assert "data" in d
