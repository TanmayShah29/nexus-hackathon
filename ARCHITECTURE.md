# NEXUS Architectural Overview

NEXUS is not a standard React/Node.js web application. It is a **Cognitive Operating System** built on top of the Model Context Protocol (MCP) and Google's ADK. Rather than hardcoding linear flows, NEXUS creates a reactive, dynamic Swarm of 9 distinct LLM personalities that converse with one another through a shared execution state known as the **Blackboard**.

Below is a breakdown of the core architectural pillars.

---

## 1. The Blackboard Pattern

At the heart of the `agents/orchestrator.py` is the `Blackboard`. 
Instead of Agent A sending a direct message to Agent B (which creates unscalable entanglement), all agents read from and write to a central shared state. 

*   **Dynamic Re-Planning**: When a user submits an intent, the Core Agent initializes the Blackboard with an **Execution Plan** (e.g., `["research_event", "check_calendar", "schedule_meeting"]`).
*   **Parallel Execution**: The `SwarmEngine` maps these tasks to specialized agents. If the `Research` agent finds that the "event" has been cancelled, it posts this finding to the Blackboard. The `Scheduler` agent, waiting in the next phase, reads the Blackboard, recognizes the cancellation, and autonomously aborts the calendar invite without the user needing to intervene.

## 2. 4-Layer Memory Persistence

LLMs suffer from limited context windows. NEXUS solves this with a multi-layered approach found in `memory/`:

1.  **Thread Memory**: A Redis/Firestore backed queue of the last 15 exact conversational turns for immediate linguistic context.
2.  **Context Memory**: Working memory injected directly into the Gemini prompt regarding the user's *current* goal or loaded files constraint.
3.  **Semantic Memory**: A Supabase Vector Storage implementation (`pgvector`). Important facts (e.g., "The user is allergic to peanuts") are converted into embeddings via `models/embedding-001` and retrieved during relevant future queries via Cosine Similarity.
4.  **Relational Memory**: (Advanced) Knowledge graphs where entities and interactions are mapped across time.

## 3. The MCP Tooling Matrix

Tools are the hands of the Swarm. We utilize the standardized **Model Context Protocol (MCP)** inside `mcp_servers/` so our agents aren't tightly coupled to specific SDK versions.

*   Every MCP server (e.g., `weather_mcp.py`, `notion_mcp.py`) is an isolated JSON-RPC endpoint.
*   The agents only know the *schema* of the tools. When Gemini requests a function call, the `Blackboard` routes the payload to the corresponding MCP server, executes the Python logic, and returns the result back to the LLM. 

## 4. Centralized Stability (Hackathon Polish)

To ensure deterministic performance for the judges:
1.  **Strict Configuration (`config.py`)**: All environment variables and API keys are parsed synchronously at boot. Zero `os.getenv` calls exist in the agent files. This prevents silent failures deep in the execution stack.
2.  **Standardized Logging (`nexus` namespace)**: Native Python `logging` captures every phase transition and JSON payload in a uniform format, preparing the app for enterprise-grade ingestion (e.g., Datadog, Databand). 
3.  **Async/Await Non-Blocking APIs**: The FastAPI routing layer uses `asyncio.to_thread` and asynchronous LLM generation streams to prevent a single complex Research task from freezing the entire Swarm engine.

---

*This architecture guarantees that as new APIs or Agent personalities are required in the future, developers only need to drop a new `.py` file into the folder without rewriting the core `SwarmEngine` router.*
