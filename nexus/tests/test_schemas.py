"""
test_schemas.py — Tests for Pydantic Schemas
"""

from nexus.models.schemas import (
    ChatRequest,
    TraceEvent,
    AgentResult,
    SuggestionChip,
    AGENT_REGISTRY,
)


class TestChatRequest:
    def test_valid_request(self):
        req = ChatRequest(prompt="Hello NEXUS")
        assert req.prompt == "Hello NEXUS"
        assert req.session_id is not None

    def test_custom_session_id(self):
        req = ChatRequest(prompt="Test", session_id="custom-id")
        assert req.session_id == "custom-id"

    def test_custom_user_id(self):
        req = ChatRequest(prompt="Test", user_id="my-user")
        assert req.user_id == "my-user"

    def test_with_plan(self):
        plan = [[{"agent": "atlas", "goal": "Find info"}]]
        req = ChatRequest(prompt="Test", plan=plan)
        assert req.plan == plan


class TestTraceEvent:
    def test_valid_event(self):
        event = TraceEvent(
            session_id="test-123",
            agent="atlas",
            agent_display_name="Atlas",
            tool="tavily_search",
            tool_display_name="Tavily",
            action="Searching...",
            status="running",
        )
        assert event.agent == "atlas"
        assert event.status == "running"

    def test_status_values(self):
        for status in ["running", "done", "error", "skipped"]:
            event = TraceEvent(
                session_id="test",
                agent="atlas",
                agent_display_name="Atlas",
                tool="test",
                tool_display_name="Test",
                action="Test",
                status=status,
            )
            assert event.status == status


class TestAgentResult:
    def test_valid_result(self):
        result = AgentResult(
            agent="atlas",
            session_id="test-123",
            summary="Found results",
            markdown_content="## Results\n\nFound 5 items",
        )
        assert result.summary == "Found results"
        assert result.agent == "atlas"

    def test_with_suggestions(self):
        result = AgentResult(
            agent="chrono",
            session_id="test",
            summary="Scheduled",
            markdown_content="Done",
            suggestions=[
                SuggestionChip(label="Next", prompt="next step", agent_hint="tasks")
            ],
        )
        assert len(result.suggestions) == 1
        assert result.suggestions[0].label == "Next"


class TestAgentRegistry:
    def test_registry_not_empty(self):
        assert len(AGENT_REGISTRY) > 0

    def test_registry_agents(self):
        agent_names = [a.name for a in AGENT_REGISTRY]
        assert "atlas" in agent_names
        assert "chrono" in agent_names
