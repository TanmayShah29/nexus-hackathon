"""
routes/system.py — NEXUS System & Health endpoints (Fixed)

FIX: Removed dead firestore_client import that crashed startup.
FIX: Uses updated HealthResponse, AgentsResponse, AgentInfo from schemas.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException

from nexus.models.schemas import (
    HealthResponse, AgentsResponse, AgentInfo, AGENT_REGISTRY, AGENT_IDENTITY_MAP,
)
from nexus.config import get_demo_mode, get_nexus_api_key, VERSION

NEXUS_API_KEY = get_nexus_api_key()
router = APIRouter(tags=["system"])
logger = logging.getLogger("nexus")

DEMO_MODE = get_demo_mode()


@router.get("/health", response_model=HealthResponse)
async def health(authorization: str = Header(None)):
    """System health check."""
    if authorization != f"Bearer {NEXUS_API_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    from nexus.memory.supabase_client import get_supabase_client
    sb = get_supabase_client()
    supabase_ok = sb.is_active()

    return HealthResponse(
        status="ok" if supabase_ok else "degraded",
        mode="demo" if DEMO_MODE else "live",
        version=VERSION,
        agents_loaded=len(AGENT_REGISTRY),
        mcp_servers_ready=8,  # calendar, gmail, weather, notion, tavily, wikipedia, executor, filesystem
    )


@router.get("/agents", response_model=AgentsResponse)
async def get_agents(authorization: str = Header(None)):
    """All registered agent identities and capabilities."""
    if authorization != f"Bearer {NEXUS_API_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    return AgentsResponse(agents=AGENT_REGISTRY, total=len(AGENT_REGISTRY))


@router.get("/agents/{agent_name}", response_model=AgentInfo)
async def get_agent(agent_name: str, authorization: str = Header(None)):
    if authorization != f"Bearer {NEXUS_API_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    identity = AGENT_IDENTITY_MAP.get(agent_name)
    if not identity:
        raise HTTPException(404, f"Agent '{agent_name}' not found")
    return AgentInfo(
        name=identity.name,
        display_name=identity.display_name,
        role=identity.role,
        color_neon=identity.color_neon,
        capabilities=identity.capabilities,
    )
