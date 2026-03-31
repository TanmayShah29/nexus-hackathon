"""
schemas.py — NEXUS Unified Schema Layer
All Pydantic models, enums, registries, and type aliases live here.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, ConfigDict

# ─────────────────────────────────────────────
# ENUMS & TYPES
# ─────────────────────────────────────────────

# FIX: Added all agent names including new specialists and "system"
AgentName = Literal[
    "orchestrator", "atlas", "chrono", "sage", "mnemo", "system",
    "goals", "analytics", "workflow", "briefing", "tasks", "booster", "tools"
]

AgentStatus = Literal["idle", "thinking", "working", "done", "error"]
TraceStatus = Literal["running", "done", "error", "skipped"]
MemoryLayer = Literal["register", "working", "daily", "eternal"]
Priority = Literal["low", "medium", "high", "urgent"]

# ─────────────────────────────────────────────
# AGENT IDENTITY
# ─────────────────────────────────────────────

class AgentIdentity(BaseModel):
    name: AgentName
    display_name: str
    role: str
    tagline: str
    personality: str
    color_neon: str
    color_soft: str
    icon_slug: str
    capabilities: List[str]


class NeuralPulse(BaseModel):
    pulse_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_node: str = "nexus-core"
    target_nodes: List[str]
    intensity: float = 1.0
    color: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ─────────────────────────────────────────────
# MCP CARD DETAIL (Tracer / SSE Detail Objects)
# ─────────────────────────────────────────────

class MCPStep(BaseModel):
    step_number: int
    title: str
    description: str = ""
    api_endpoint: Optional[str] = None
    result_summary: Optional[str] = None
    tag: Optional[str] = None
    tag_type: Optional[str] = None  # "success" | "warning" | "error"


class StateWrite(BaseModel):
    key: str
    value_summary: str
    written_by: AgentName
    read_by: Optional[List[str]] = None


class MemoryWrite(BaseModel):
    layer: str
    layer_display: str
    content: str
    importance_score: Optional[int] = None


class ConflictResolution(BaseModel):
    conflict: str
    resolution: str
    resolution_type: str = "auto"


class MCPCardDetail(BaseModel):
    agent: AgentName
    agent_display_name: str
    tool: str
    tool_display_name: str
    status: TraceStatus = "done"
    api_calls_made: int = 1
    duration_ms: Optional[int] = None
    steps: List[MCPStep] = Field(default_factory=list)
    session_state_writes: List[StateWrite] = Field(default_factory=list)
    memory_writes: List[MemoryWrite] = Field(default_factory=list)
    conflicts_resolved: List[ConflictResolution] = Field(default_factory=list)
    raw_output_summary: Optional[str] = None
    resource_id: Optional[str] = None
    resource_link: Optional[str] = None


# ─────────────────────────────────────────────
# TRACE & COMMUNICATION
# ─────────────────────────────────────────────

class TraceEvent(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    agent: AgentName
    agent_display_name: str = ""
    tool: str = ""
    tool_display_name: str = ""
    action: str
    status: TraceStatus
    detail: Optional[MCPCardDetail] = None
    workflow_step: Optional[int] = None
    workflow_total_steps: Optional[int] = None
    pulsing: bool = False


class SuggestionChip(BaseModel):
    label: str
    prompt: str
    context_hint: Optional[str] = None
    agent_hint: Optional[str] = None


class AgentResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    agent: AgentName
    session_id: str
    summary: str
    markdown_content: str = ""
    # Support both old (full_response) and new (markdown_content) field names
    full_response: Optional[str] = None
    suggestions: List[SuggestionChip] = Field(default_factory=list)
    metrics: Dict[str, Union[int, float]] = Field(default_factory=dict)
    confidence: float = 1.0
    workflow_type: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    memory_writes: List[MemoryWrite] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def get_content(self) -> str:
        """Return the main textual content regardless of which field was set."""
        return self.markdown_content or self.full_response or ""


# ─────────────────────────────────────────────
# CHAT REQUEST
# ─────────────────────────────────────────────

class ChatRequest(BaseModel):
    prompt: str
    user_id: str = "default_user"
    session_id: str = Field(default_factory=lambda: f"nexus-{uuid.uuid4().hex[:8]}")
    plan: Optional[List[List[Dict[str, str]]]] = None


# ─────────────────────────────────────────────
# MEMORY MODELS
# ─────────────────────────────────────────────

class MemoryNode(BaseModel):
    id: str
    label: str
    layer: str
    radius: int = 12
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MemoryLink(BaseModel):
    source: str
    target: str
    strength: float = 0.5
    color: Optional[str] = None


class MemoryGraph(BaseModel):
    nodes: List[MemoryNode]
    links: List[MemoryLink]


class MemoryEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    layer: str
    content: str
    agent_source: AgentName
    tags: List[str] = Field(default_factory=list)
    importance_score: int = 1
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    embedding_stub: Optional[List[float]] = None


# Memory route response models
class UserMemory(BaseModel):
    user_id: str
    working: Dict[str, Any] = Field(default_factory=dict)
    daily: List[Any] = Field(default_factory=list)
    profile: List[MemoryEntry] = Field(default_factory=list)
    semantic_results: List[MemoryEntry] = Field(default_factory=list)


class Node(BaseModel):
    id: str
    label: str
    type: str = "semantic"
    r: int = 12


class Link(BaseModel):
    source: str
    target: str
    type: str = "related"


class GraphData(BaseModel):
    nodes: List[Node]
    links: List[Link]


# ─────────────────────────────────────────────
# SYSTEM / HEALTH
# ─────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "ready"
    mode: str = "demo"
    version: str = "1.0.0"
    agents_loaded: int = 0
    mcp_servers_ready: int = 0


class AgentInfo(BaseModel):
    name: AgentName
    display_name: str
    role: str
    color_neon: str
    capabilities: List[str]


class AgentsResponse(BaseModel):
    agents: List[AgentInfo]
    total: int


# ─────────────────────────────────────────────
# REGISTRIES
# ─────────────────────────────────────────────

# FIX: Added "system" and all new agent names to AGENT_IDENTITY_MAP
AGENT_IDENTITY_MAP: Dict[AgentName, AgentIdentity] = {
    "atlas": AgentIdentity(
        name="atlas", display_name="Atlas", role="Intelligence Specialist",
        tagline="Web Synthesis & Analytical Search",
        personality="Precise, academic, and deeply analytical.",
        color_neon="#1a73e8", color_soft="#E8F0FE", icon_slug="globe-alt",
        capabilities=["Web Intelligence", "Syllabus Extraction", "Data Synthesis"]
    ),
    "chrono": AgentIdentity(
        name="chrono", display_name="Chrono", role="Action Specialist",
        tagline="Time, Tasks & Commitments",
        personality="Punctual, organized, and focused on execution.",
        color_neon="#EA4335", color_soft="#FCE8E6", icon_slug="clock",
        capabilities=["Calendar Sync", "Task Decomposition", "Goal Tracking"]
    ),
    "sage": AgentIdentity(
        name="sage", display_name="Sage", role="Structure Specialist",
        tagline="Knowledge Architecture & Strategy",
        personality="Philosophical, strategic, and focused on long-term growth.",
        color_neon="#34A853", color_soft="#E6F4EA", icon_slug="academic-cap",
        capabilities=["Strategy Roadmaps", "Note Architecture", "Semantic Linking"]
    ),
    "mnemo": AgentIdentity(
        name="mnemo", display_name="Mnemo", role="Memory Specialist",
        tagline="Total Semantic Recall",
        personality="Ambient, quiet, and deeply intuitive.",
        color_neon="#9334E6", color_soft="#F3E8FD", icon_slug="sparkles",
        capabilities=["Semantic Retrieval", "Preference Learning", "Identity Persistence"]
    ),
    "orchestrator": AgentIdentity(
        name="orchestrator", display_name="Architect", role="Lead Orchestrator",
        tagline="The Neural Conductor",
        personality="Calm, visionary, and authoritative.",
        color_neon="#4285F4", color_soft="#E8F0FE", icon_slug="squares-plus",
        capabilities=["Phase Planning", "Swarm Consensus", "Conflict Resolution"]
    ),
    # FIX: Added missing agent identities
    "system": AgentIdentity(
        name="system", display_name="System", role="Core System",
        tagline="Internal NEXUS Operations",
        personality="Silent, reliable, foundational.",
        color_neon="#888888", color_soft="#F0F0F0", icon_slug="cog",
        capabilities=["Session Management", "Error Handling", "Health Checks"]
    ),
    "goals": AgentIdentity(
        name="goals", display_name="Goals", role="Strategy Specialist",
        tagline="90-Day Roadmapping & OKRs",
        personality="Ambitious, structured, milestone-driven.",
        color_neon="#F9AB00", color_soft="#FEF3C7", icon_slug="flag",
        capabilities=["Goal Decomposition", "Milestone Tracking", "Progress Analysis"]
    ),
    "analytics": AgentIdentity(
        name="analytics", display_name="Analytics", role="Data Specialist",
        tagline="Productivity Reports & Pattern Analysis",
        personality="Data-driven, precise, insightful.",
        color_neon="#00BCD4", color_soft="#E0F7FA", icon_slug="chart-bar",
        capabilities=["Productivity Metrics", "Pattern Detection", "Weekly Reports"]
    ),
    "workflow": AgentIdentity(
        name="workflow", display_name="Workflow", role="Pipeline Specialist",
        tagline="Multi-Agent Task Pipelines",
        personality="Systematic, efficient, coordination-focused.",
        color_neon="#FF7043", color_soft="#FBE9E7", icon_slug="arrows",
        capabilities=["Pipeline Optimization", "Agent Coordination", "Step Verification"]
    ),
    "briefing": AgentIdentity(
        name="briefing", display_name="Briefing", role="Context Specialist",
        tagline="Daily Synthesis & Adaptive Communication",
        personality="Warm, contextual, situationally aware.",
        color_neon="#26A69A", color_soft="#E0F2F1", icon_slug="newspaper",
        capabilities=["Morning Briefings", "Weather Context", "Adaptive Responses"]
    ),
    "tasks": AgentIdentity(
        name="tasks", display_name="Tasks", role="Execution Specialist",
        tagline="Task Management & Execution",
        personality="Action-oriented, detail-focused, reliable.",
        color_neon="#AB47BC", color_soft="#F3E5F5", icon_slug="check-circle",
        capabilities=["Task Creation", "Priority Management", "Completion Tracking"]
    ),
    "booster": AgentIdentity(
        name="booster", display_name="Booster", role="Performance Engine",
        tagline="Zero-Latency Local Logic",
        personality="Fast, deterministic, bypass-first.",
        color_neon="#FFFFFF", color_soft="#F5F5F5", icon_slug="bolt",
        capabilities=["Math Evaluation", "Date/Time", "Table Formatting"]
    ),
    "tools": AgentIdentity(
        name="tools", display_name="Toolbox", role="Utility Specialist",
        tagline="External API & Utility Integration",
        personality="Efficient, connected, and highly versatile.",
        color_neon="#00E676", color_soft="#E8F5E9", icon_slug="wrench",
        capabilities=["Currency Conversion", "Crypto Tracking", "World News", "Definitions"]
    ),
}

# Flat registry for /agents endpoint
AGENT_REGISTRY: List[AgentInfo] = [
    AgentInfo(
        name=identity.name,
        display_name=identity.display_name,
        role=identity.role,
        color_neon=identity.color_neon,
        capabilities=identity.capabilities,
    )
    for identity in AGENT_IDENTITY_MAP.values()
    if identity.name not in ("system", "booster")
]

# Quick lookup map
AGENT_MAP: Dict[str, AgentInfo] = {a.name: a for a in AGENT_REGISTRY}
