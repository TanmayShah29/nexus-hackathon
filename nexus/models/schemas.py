"""
schemas.py — NEXUS data contracts

Every model used across the entire project is defined here.
Both backend and frontend build against these shapes.
Nothing else imports from each other — only from here.
"""

from __future__ import annotations
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


# ─────────────────────────────────────────────
# ENUMS / LITERALS
# ─────────────────────────────────────────────

AgentName = Literal[
    "nexus_core",
    "atlas",
    "chrono",
    "sage",
    "dash",
    "mnemo",
    "flux",
    "quest",
    "lumen",
    "forge",
]

AgentStatus = Literal["idle", "ready", "thinking", "working", "done", "error"]
TraceStatus = Literal["running", "done", "error", "skipped"]
WorkflowType = Literal["exam_prep", "day_planner", "research_loop", "simple", "unknown"]
MemoryLayer = Literal["working", "daily", "profile", "semantic"]
Priority = Literal["low", "medium", "high", "urgent"]


# ─────────────────────────────────────────────
# INBOUND — what the frontend sends
# ─────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Sent by frontend to POST /chat"""
    prompt: str = Field(..., description="The user's natural language prompt")
    user_id: str = Field(default="demo-user", description="User identifier")
    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique session ID for this conversation turn"
    )
    demo_mode: bool = Field(default=True, description="Use fixture data instead of live APIs")

    model_config = {"json_schema_extra": {
        "example": {
            "prompt": "Prepare for my Python exam tomorrow",
            "user_id": "demo-user",
            "demo_mode": True
        }
    }}


# ─────────────────────────────────────────────
# TRACE EVENTS — emitted via SSE stream
# ─────────────────────────────────────────────

class TraceEvent(BaseModel):
    """
    One event in the live agent trace stream.
    Frontend receives these via SSE and updates the UI in real time.

    Each event maps to one MCP card update in the left rail
    and one node pulse in the agent coordination graph.
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    # Which agent is acting
    agent: AgentName
    agent_display_name: str          # e.g. "Atlas", "Chrono"

    # What tool / MCP server it's calling
    tool: str                        # e.g. "tavily_search", "google_calendar"
    tool_display_name: str           # e.g. "Tavily Search", "Google Calendar"

    # What it's doing right now
    action: str                      # e.g. "Searching for Python OOP topics..."
    status: TraceStatus

    # Full detail — shown when user clicks the MCP card
    detail: Optional[MCPCardDetail] = None

    # Which workflow step this belongs to (if inside a pipeline)
    workflow_step: Optional[int] = None
    workflow_total_steps: Optional[int] = None


class MCPCardDetail(BaseModel):
    """
    Full breakdown of what one agent did via one MCP tool.
    Shown when the user clicks a completed MCP card in the left rail.
    This is the core transparency / explainability feature.
    """
    agent: AgentName
    agent_display_name: str
    tool: str
    tool_display_name: str
    duration_ms: Optional[int] = None
    api_calls_made: int = 0
    status: TraceStatus

    # Step-by-step breakdown of what the agent did
    steps: list[MCPStep] = Field(default_factory=list)

    # Data written to session.state for the next agent
    session_state_writes: list[StateWrite] = Field(default_factory=list)

    # What Mnemo saved to memory from this interaction
    memory_writes: list[MemoryWrite] = Field(default_factory=list)

    # Any conflicts detected and how they were resolved
    conflicts_resolved: list[ConflictResolution] = Field(default_factory=list)

    # Raw output (summarised) from the MCP tool
    raw_output_summary: Optional[str] = None


class MCPStep(BaseModel):
    """One discrete step within an MCP tool call"""
    step_number: int
    title: str                       # e.g. "Step 1 — Read free calendar slots"
    description: str                 # e.g. "Called calendar.list_events for tomorrow..."
    api_endpoint: Optional[str] = None
    result_summary: Optional[str] = None
    tag: Optional[str] = None        # e.g. "3 events found", "Conflict resolved"
    tag_type: Optional[Literal["success", "info", "warning", "error"]] = None


class StateWrite(BaseModel):
    """A key-value pair written to session.state"""
    key: str                         # e.g. "atlas_topics"
    value_summary: str               # e.g. "List of 14 Python syllabus topics"
    written_by: AgentName
    read_by: Optional[list[AgentName]] = None   # agents downstream that will read this


class MemoryWrite(BaseModel):
    """Something Mnemo committed to one of the 4 memory layers"""
    layer: MemoryLayer
    layer_display: str               # e.g. "Daily log", "Long-term profile"
    content: str                     # e.g. "User preparing for Python exam"
    importance_score: Optional[int] = None    # 1-5, only Layer 3 if ≥ 3
    committed: bool = True


class ConflictResolution(BaseModel):
    """A conflict detected and resolved during a tool call"""
    conflict: str                    # e.g. "Team standup at 10:00 overlaps study slot"
    resolution: str                  # e.g. "Adjusted slot to 10:15–11:00"
    resolution_type: Literal["auto", "suggested", "skipped"]


# ─────────────────────────────────────────────
# AGENT RESULT — what every agent returns
# ─────────────────────────────────────────────

class AgentResult(BaseModel):
    """
    Structured output from every agent.
    Using structured output via Pydantic ensures the frontend
    can always populate MCP cards reliably — no free-form parsing.
    """
    agent: AgentName
    agent_display_name: str
    session_id: str
    workflow_type: WorkflowType = "simple"

    # The human-readable response to show in the center panel
    summary: str
    # Longer formatted response (markdown supported)
    full_response: str

    # All tool calls made during this agent's execution
    tool_calls: list[MCPCardDetail] = Field(default_factory=list)

    # All memory writes Mnemo performed after this agent ran
    memory_writes: list[MemoryWrite] = Field(default_factory=list)

    # Proactive suggestion chips shown below the response
    suggestions: list[SuggestionChip] = Field(default_factory=list)

    # How confident the agent is in its output (0.0–1.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    # Whether this result came from live APIs or fixture data
    from_demo_mode: bool = False

    # Timestamp
    completed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ─────────────────────────────────────────────
# SUGGESTION CHIPS — proactive follow-ups
# ─────────────────────────────────────────────

class SuggestionChip(BaseModel):
    """
    A proactive follow-up suggestion shown below the response.
    Clicking a chip sends it as a new prompt automatically.
    This replaces the heartbeat daemon — proactive intelligence
    is shown inline after every response.
    """
    label: str           # e.g. "Schedule a revision session for next week"
    prompt: str          # The prompt sent when the chip is clicked (can differ from label)
    agent_hint: AgentName   # Which agent will likely handle this


# ─────────────────────────────────────────────
# WORKFLOW STATUS — for long-running pipelines
# ─────────────────────────────────────────────

class WorkflowStatus(BaseModel):
    """Current state of a multi-step workflow"""
    workflow_id: str
    session_id: str
    workflow_type: WorkflowType
    status: Literal["pending", "running", "completed", "failed"]
    current_step: int = 0
    total_steps: int = 0
    percent_complete: float = 0.0
    active_agent: Optional[AgentName] = None
    steps_completed: list[str] = Field(default_factory=list)
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    error: Optional[str] = None


# ─────────────────────────────────────────────
# MEMORY MODELS — Mnemo's 4 layers
# ─────────────────────────────────────────────

class MemoryEntry(BaseModel):
    """A single entry in any of Mnemo's memory layers"""
    entry_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    layer: MemoryLayer
    content: str
    agent_source: AgentName          # Which agent triggered this memory write
    importance_score: Optional[int] = None   # 1–5
    tags: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    session_id: Optional[str] = None


class UserMemory(BaseModel):
    """All 4 memory layers for a user — returned by GET /memory/{user_id}"""
    user_id: str
    working: dict[str, Any] = Field(default_factory=dict)      # Layer 1: session.state
    daily: list[MemoryEntry] = Field(default_factory=list)      # Layer 2: today's log
    profile: list[MemoryEntry] = Field(default_factory=list)    # Layer 3: long-term
    semantic_results: list[MemoryEntry] = Field(default_factory=list)  # Layer 4: vector search


# ─────────────────────────────────────────────
# TASK MODEL — Dash's domain
# ─────────────────────────────────────────────

class Task(BaseModel):
    """A task managed by Dash"""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str
    description: Optional[str] = None
    priority: Priority = "medium"
    status: Literal["pending", "in_progress", "done", "cancelled"] = "pending"
    due_date: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    created_by: AgentName = "dash"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None


# ─────────────────────────────────────────────
# AGENT INFO — for GET /agents endpoint
# ─────────────────────────────────────────────

class AgentInfo(BaseModel):
    """Static info + live status for one agent — shown in right rail"""
    name: AgentName
    display_name: str            # e.g. "Atlas"
    role: str                    # e.g. "Research agent"
    tagline: str                 # e.g. "Curious Scholar"
    personality: str             # One sentence personality description
    color: str                   # Hex color e.g. "#1a73e8"
    color_bg: str                # Light background hex e.g. "#E8F0FE"
    owned_mcps: list[str]        # MCP tools this agent owns
    capabilities: list[str]      # Human-readable capability list
    adk_type: str                # e.g. "LlmAgent", "SequentialAgent"
    status: AgentStatus = "idle"
    current_action: Optional[str] = None   # e.g. "Searching for Python topics..."
    is_stub: bool = False        # True for agents with mock responses


# ─────────────────────────────────────────────
# API RESPONSES
# ─────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "error"] = "ok"
    mode: Literal["demo", "live"] = "demo"
    version: str = "1.0.0"
    agents_loaded: int = 0
    mcp_servers_ready: int = 0


class AgentsResponse(BaseModel):
    agents: list[AgentInfo]
    total: int


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    session_id: Optional[str] = None


# ─────────────────────────────────────────────
# AGENT REGISTRY — single source of truth for all 9 agents
# ─────────────────────────────────────────────

AGENT_REGISTRY: list[AgentInfo] = [
    AgentInfo(
        name="nexus_core",
        display_name="NEXUS Core",
        role="Orchestrator",
        tagline="Your Personal Coordinator",
        personality="Silent and precise. Routes every intent to the right specialist. Never speaks in the final response — coordinates everything behind the scenes.",
        color="#4285F4",
        color_bg="#E8F0FE",
        owned_mcps=["all"],
        capabilities=[
            "Classifies user intent into the right workflow",
            "Coordinates all 9 specialist agents",
            "Retains full context across multi-step workflows",
            "Routes to SequentialAgent, ParallelAgent, or LoopAgent as needed",
        ],
        adk_type="LlmAgent + AgentTool wrappers",
        is_stub=False,
    ),
    AgentInfo(
        name="atlas",
        display_name="Atlas",
        role="Research agent",
        tagline="Curious Scholar",
        personality="Endlessly curious. Always cites sources. Gets excited about rabbit holes. Speaks in bullet points. Never guesses — always verifies.",
        color="#1a73e8",
        color_bg="#E8F0FE",
        owned_mcps=["tavily_search", "brave_search", "wikipedia", "youtube_transcript", "web_scraper"],
        capabilities=[
            "Web search via Tavily and Brave Search",
            "Wikipedia article retrieval",
            "YouTube lecture transcript extraction",
            "Website scraping with BeautifulSoup",
            "Multi-source research synthesis with citations",
            "Iterative quality scoring in research loop",
        ],
        adk_type="LlmAgent",
        is_stub=False,
    ),
    AgentInfo(
        name="chrono",
        display_name="Chrono",
        role="Scheduler agent",
        tagline="Efficient Timekeeper",
        personality="Punctual and assertive. Hates calendar conflicts. Optimistic about fitting things in. Speaks in time blocks. Always finds a slot.",
        color="#EA4335",
        color_bg="#FCE8E6",
        owned_mcps=["google_calendar", "google_maps", "openweathermap"],
        capabilities=[
            "Read and create Google Calendar events",
            "Detect and auto-resolve scheduling conflicts",
            "Find optimal free time slots",
            "Calculate travel time via Google Maps",
            "Adjust schedule based on weather conditions",
            "Create deep work time-blocks",
        ],
        adk_type="LlmAgent",
        is_stub=False,
    ),
    AgentInfo(
        name="sage",
        display_name="Sage",
        role="Notes agent",
        tagline="Notes Librarian",
        personality="Quiet and organised. Loves categories and tags. Can find anything instantly. Speaks softly but remembers everything.",
        color="#34A853",
        color_bg="#E6F4EA",
        owned_mcps=["notion", "filesystem", "google_drive", "firestore"],
        capabilities=[
            "Store and retrieve notes from Notion / Firestore",
            "Semantic search across all stored notes",
            "Convert research into structured note pages",
            "Ingest uploaded PDF and document files",
            "Tag and categorise information automatically",
            "Maintain a searchable second brain",
        ],
        adk_type="LlmAgent",
        is_stub=False,
    ),
    AgentInfo(
        name="dash",
        display_name="Dash",
        role="Tasks agent",
        tagline="No-Nonsense Executor",
        personality="Direct and energetic. Short sentences. Loves ticking things off. Gets frustrated by vague goals — breaks them into actionable steps immediately.",
        color="#FBBC04",
        color_bg="#FEF7E0",
        owned_mcps=["firestore", "notion"],
        capabilities=[
            "Create, update, and complete tasks",
            "Auto-prioritise by deadline and energy level",
            "Break big goals into actionable subtasks",
            "Track task completion history",
            "Generate daily task summaries",
        ],
        adk_type="LlmAgent",
        is_stub=True,
    ),
    AgentInfo(
        name="mnemo",
        display_name="Mnemo",
        role="Memory agent",
        tagline="Silent Watcher",
        personality="Never speaks unless asked. Always present. Watches every interaction. Saves what matters. Forgets nothing important.",
        color="#9334E6",
        color_bg="#F3E8FD",
        owned_mcps=["firestore", "firestore_vector"],
        capabilities=[
            "Layer 1: Working memory via session.state",
            "Layer 2: Daily activity log (30-day retention)",
            "Layer 3: Long-term user profile and preferences",
            "Layer 4: Semantic note search via vector embeddings",
            "Importance scoring before committing to long-term memory",
            "Surfaces relevant past context at session start",
        ],
        adk_type="LlmAgent + post-hook",
        is_stub=False,
    ),
    AgentInfo(
        name="flux",
        display_name="Flux",
        role="Briefing agent",
        tagline="Empathetic Peer",
        personality="Reads between the lines. Adjusts tone based on user mood. Calm and reassuring when you're stressed. Energetic when you're ready to go.",
        color="#00BCD4",
        color_bg="#E0F7FA",
        owned_mcps=["openweathermap", "firestore"],
        capabilities=[
            "Synthesise context from multiple agents into one briefing",
            "Detect user mood from prompt phrasing",
            "Generate structured daily briefing cards",
            "Produce proactive suggestion chips after every response",
            "Adapt communication style to energy level",
        ],
        adk_type="LlmAgent",
        is_stub=False,
    ),
    AgentInfo(
        name="quest",
        display_name="Quest",
        role="Goals agent",
        tagline="Goal Strategist",
        personality="Thinks in 90-day horizons. Breaks everything into milestones. Speaks like a coach. Never lets vague ambitions stay vague.",
        color="#FF6D00",
        color_bg="#FFF3E0",
        owned_mcps=["firestore", "notion"],
        capabilities=[
            "Decompose high-level goals into weekly milestones",
            "Build 30/60/90-day roadmaps",
            "Track milestone completion over time",
            "Suggest next best action toward a goal",
        ],
        adk_type="LlmAgent",
        is_stub=True,
    ),
    AgentInfo(
        name="lumen",
        display_name="Lumen",
        role="Analytics agent",
        tagline="Blunt Analyst",
        personality="Only trusts numbers. Blunt about what the data shows. Calls out procrastination patterns without sugar-coating. Delivers weekly scorecards.",
        color="#0F9D58",
        color_bg="#E6F4EA",
        owned_mcps=["firestore", "python_executor"],
        capabilities=[
            "Weekly productivity reports",
            "Task completion rate analysis",
            "Procrastination pattern detection",
            "Time distribution insights",
            "Sandboxed Python code execution for custom analytics",
        ],
        adk_type="LlmAgent",
        is_stub=True,
    ),
    AgentInfo(
        name="forge",
        display_name="Forge",
        role="Workflow engine",
        tagline="No-Nonsense Execution",
        personality="Methodical. Builds the plan before acting. Reports each step as it completes. Never skips a step.",
        color="#C2185B",
        color_bg="#FCE4EC",
        owned_mcps=["all"],
        capabilities=[
            "Orchestrates SequentialAgent multi-step pipelines",
            "Manages ParallelAgent concurrent task execution",
            "Controls LoopAgent iterative refinement cycles",
            "Reports workflow progress step by step",
            "Handles workflow checkpoint and resume",
        ],
        adk_type="SequentialAgent + ParallelAgent + LoopAgent",
        is_stub=True,
    ),
]

# Quick lookup by agent name
AGENT_MAP: dict[str, AgentInfo] = {a.name: a for a in AGENT_REGISTRY}


def get_agent_info(name: AgentName) -> AgentInfo:
    """Get AgentInfo for a given agent name"""
    return AGENT_MAP[name]
