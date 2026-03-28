"""Quick test — run this to verify schemas.py is working"""
import sys
sys.path.insert(0, '.')

from models.schemas import (
    ChatRequest, TraceEvent, AgentResult, MCPCardDetail,
    UserMemory, Task, SuggestionChip, WorkflowStatus,
    AGENT_REGISTRY, get_agent_info, HealthResponse
)

print("Testing ChatRequest...")
req = ChatRequest(prompt="Prepare for my exam tomorrow")
print(f"  ✓ prompt='{req.prompt}', session_id='{req.session_id[:8]}...'")

print("Testing TraceEvent...")
event = TraceEvent(
    session_id="test-123",
    agent="atlas",
    agent_display_name="Atlas",
    tool="tavily_search",
    tool_display_name="Tavily Search",
    action="Searching for Python OOP topics...",
    status="running"
)
print(f"  ✓ agent='{event.agent}', status='{event.status}'")

print("Testing AgentResult...")
result = AgentResult(
    agent="atlas",
    agent_display_name="Atlas",
    session_id="test-123",
    summary="Found 14 Python topics",
    full_response="## Research Results\n\nFound 14 topics in the syllabus...",
    suggestions=[
        SuggestionChip(
            label="Create a study schedule",
            prompt="Block study time for my Python exam tomorrow",
            agent_hint="chrono"
        )
    ]
)
print(f"  ✓ summary='{result.summary}', suggestions={len(result.suggestions)}")

print("Testing AGENT_REGISTRY...")
print(f"  ✓ {len(AGENT_REGISTRY)} agents registered")
for agent in AGENT_REGISTRY:
    stub = " (stub)" if agent.is_stub else ""
    print(f"    - {agent.display_name:12s} [{agent.color}]{stub}")

print("Testing get_agent_info...")
atlas = get_agent_info("atlas")
print(f"  ✓ Atlas: {atlas.tagline}, color={atlas.color}")

print("Testing Task...")
task = Task(user_id="demo-user", title="Review Python OOP chapter", priority="high")
print(f"  ✓ task='{task.title}', priority='{task.priority}'")

print("\n✅ All schemas OK — Phase 1 complete!")
