"""
routes/memory.py — Memory API endpoints (Fixed)
"""
from __future__ import annotations

import logging
from fastapi import APIRouter, Header, HTTPException

from nexus.models.schemas import UserMemory, MemoryEntry, GraphData, Node, Link
from nexus.memory.supabase_client import get_supabase_client
from nexus.memory.vector_store import VectorStore
from nexus.config import get_nexus_api_key

NEXUS_API_KEY = get_nexus_api_key()
router = APIRouter(tags=["memory"])
logger = logging.getLogger("nexus")


@router.get("/memory/{user_id}", response_model=UserMemory)
async def get_memory(user_id: str, authorization: str = Header(None)):
    """All 4 memory layers for a user."""
    if authorization != f"Bearer {NEXUS_API_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    sb = get_supabase_client()
    vs = VectorStore()

    # L3: Context items
    context_data = sb.get_context("memory.context") or []
    profile = [
        MemoryEntry(
            user_id=user_id,
            layer="daily",
            content=str(c),
            agent_source="mnemo",
            importance_score=3,
        )
        for c in context_data
    ]

    # FIX: Use _get_recent() via empty search so we get actual rows back
    notes = await vs.search("", top_k=20)
    semantic_results = [
        MemoryEntry(
            user_id=user_id,
            layer="eternal",
            content=n["content"],
            agent_source=n["metadata"].get("agent", "mnemo"),
            importance_score=5,
            tags=n["metadata"].get("tags", []),
        )
        for n in notes
    ]

    return UserMemory(
        user_id=user_id,
        working={},
        daily=[],
        profile=profile,
        semantic_results=semantic_results,
    )


@router.get("/memory-graph/{user_id}", response_model=GraphData)
async def get_memory_graph(user_id: str, authorization: str = Header(None)):
    """D3-friendly graph of knowledge nodes."""
    if authorization != f"Bearer {NEXUS_API_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    vs = VectorStore()
    nodes = [
        Node(
            id=node_id,
            label=node_data["label"],
            type=node_data["metadata"].get("type", "semantic"),
            r=12,
        )
        for node_id, node_data in vs.kg.nodes.items()
    ]
    links = [
        Link(source=source, target=target, type=relation)
        for source, target, relation in vs.kg.edges
    ]
    return GraphData(nodes=nodes, links=links)


@router.get("/memory-search")
async def search_memories(
    query: str, user_id: str = "demo-user", limit: int = 5, authorization: str = Header(None)
):
    """Semantic search across the vector store."""
    if authorization != f"Bearer {NEXUS_API_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    vs = VectorStore()
    return await vs.search(query, top_k=limit)
