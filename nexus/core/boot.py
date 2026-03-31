"""
core/boot.py — NEXUS Centralized Boot Sequence (Fixed)

Fixed: All imports use nexus. package prefix.
Fixed: VectorStore.load() is synchronous — removed spurious async/except pattern.
Fixed: boot() is only ever called once (idempotent guard).
"""
from __future__ import annotations

import logging

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("nexus")


class NexusState:
    def __init__(self):
        self.blackboard = None
        self.vector_store = None
        self.orchestrator = None
        self.is_booted = False


state = NexusState()


async def boot() -> NexusState:
    """
    Centralized Boot Sequence.
    Initialises Blackboard (with L2 disk restore), VectorStore, and SwarmEngine.
    Safe to call multiple times — exits early if already booted.
    """
    global state
    if state.is_booted:
        logger.warning("NEXUS Core | System already booted — skipping.")
        return state

    logger.info("NEXUS Core | Initiating Neural Boot Sequence…")

    from nexus.agents.blackboard import Blackboard
    from nexus.memory.vector_store import VectorStore
    from nexus.agents.orchestrator import SwarmEngine

    # L1 + L2: In-memory Blackboard with disk restore
    state.blackboard = Blackboard()
    await state.blackboard.load()
    logger.info("NEXUS Core | Blackboard ready.")

    # L4: Vector store (sync load from disk / Supabase init)
    state.vector_store = VectorStore()
    # VectorStore.load() is synchronous — called in __init__ already
    logger.info("NEXUS Core | Vector Memory online.")

    # Orchestrator
    state.orchestrator = SwarmEngine(state.blackboard)
    logger.info("NEXUS Core | Swarm Orchestrator online.")

    state.is_booted = True
    logger.info("NEXUS Core | Boot complete. System Ready.")
    return state
