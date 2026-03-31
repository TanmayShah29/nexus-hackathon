"""Quick test — run this to verify agent_tracer.py is working"""

import asyncio

from nexus.observability.agent_tracer import (
    AgentTracer,
    TraceStore,
    build_mcp_detail,
)

print("Testing AgentTracer emit...")
tracer = AgentTracer("test-session-001")

tracer.emit("atlas", "tavily_search", "Searching for Python OOP topics...", "running")
tracer.emit(
    "atlas",
    "tavily_search",
    "Found 14 topics",
    "done",
    detail=build_mcp_detail(
        agent="atlas",
        tool="tavily_search",
        steps=[
            {
                "title": "Step 1 — Search Tavily",
                "description": "Called Tavily API with query 'Python OOP syllabus 2024'",
                "result_summary": "Found 14 topics across 6 sources",
                "tag": "14 topics found",
                "tag_type": "success",
            }
        ],
        state_writes=[
            {
                "key": "research_topics",
                "value_summary": "List of 14 Python OOP topics",
                "read_by": ["sage", "chrono"],
            }
        ],
        raw_output_summary="OOP, decorators, async/await, data structures, testing...",
        api_calls_made=1,
    ),
)
tracer.emit(
    "chrono", "google_calendar", "Checking free slots for tomorrow...", "running"
)
tracer.emit("chrono", "google_calendar", "Found 3 free slots", "done")
tracer.emit_memory_save("Saved: user preparing for Python exam, prefers morning study")
tracer.complete()

print(f"  ✓ {len(tracer)} events emitted")

print("\nTesting get_trace...")
trace = tracer.get_trace()
print(f"  ✓ session_id: {trace['session_id']}")
print(f"  ✓ agents involved: {trace['agents_involved']}")
print(f"  ✓ tools called: {trace['tools_called']}")
print(f"  ✓ total events: {trace['total_events']}")

print("\nTesting get_mcp_detail...")
detail = tracer.get_mcp_detail("tavily_search")
print(f"  ✓ tool: {detail.tool_display_name}")
print(f"  ✓ steps: {len(detail.steps)}")
print(f"  ✓ step 1: {detail.steps[0].title}")
print(
    f"  ✓ state writes: {detail.session_state_writes[0].key} → {detail.session_state_writes[0].value_summary}"
)

print("\nTesting TraceStore...")
store = TraceStore()
t1 = store.create("session-A")
t2 = store.create("session-B")
t1.emit("sage", "notion", "Creating note pages...", "running")
found = store.get("session-A")
print(f"  ✓ store has {len(store)} sessions")
print(f"  ✓ retrieved session-A, events: {len(found)}")

print("\nTesting SSE stream (first 3 chunks)...")


async def test_stream():
    tracer2 = AgentTracer("test-stream-001")
    tracer2.emit("atlas", "wikipedia", "Looking up quantum computing...", "running")
    tracer2.emit("atlas", "wikipedia", "Retrieved article (2,400 words)", "done")
    tracer2.complete()

    chunks = []
    async for chunk in tracer2.stream():
        chunks.append(chunk)
        if len(chunks) >= 3:
            break

    for i, chunk in enumerate(chunks):
        print(f"  chunk {i + 1}: {chunk[:80].strip()}...")
    print(f"  ✓ SSE stream working, {len(chunks)} chunks received")


asyncio.run(test_stream())

print("\n✅ AgentTracer OK!")
