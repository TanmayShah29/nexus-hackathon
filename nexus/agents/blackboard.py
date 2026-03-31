"""
blackboard.py — NEXUS Shared State (Fixed)
"""
from __future__ import annotations

import os
import json
import time
import asyncio
import fcntl
from typing import Any, Dict, List
from pydantic import BaseModel, Field, PrivateAttr
import logging
logger = logging.getLogger("nexus")


def _set_recursive(d: Dict, keys: List[str], value: Any):
    if len(keys) == 1:
        d[keys[0]] = value
    else:
        key = keys[0]
        if key not in d or not isinstance(d[key], dict):
            d[key] = {}
        _set_recursive(d[key], keys[1:], value)


class Blackboard(BaseModel):
    """
    Central intelligence hub for a swarm session.
    L1 (reactive in-memory) + L2 (JSON disk) + L3 (Supabase sync).
    """

    session_id: str = "demo-session"
    user_id: str = "demo-user"

    data: Dict[str, Any] = Field(default_factory=dict)
    history: List[Dict[str, Any]] = Field(default_factory=list)

    _dirty: bool = PrivateAttr(default=False)
    _lock: asyncio.Lock = PrivateAttr(default_factory=asyncio.Lock)

    # FIX: Use __file__-relative path so it works regardless of CWD
    @property
    def _storage_path(self) -> str:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, "storage", "blackboard.json")

    def set(self, key: str, value: Any, agent_id: str = "system"):
        keys = key.split(".")
        _set_recursive(self.data, keys, value)
        self.history.append({
            "timestamp": time.time(),
            "event": "state_update",
            "key": key,
            "agent": agent_id,
            "summary": str(value)[:200],
        })
        self._dirty = True
        logger.debug(f"Blackboard | Set '{key}' by '{agent_id}'")

    def get(self, key: str, default: Any = None) -> Any:
        res = self.data
        try:
            for part in key.split("."):
                res = res[part]
            return res
        except (KeyError, TypeError):
            return default

    async def save(self):
        if not self._dirty:
            return

        async with self._lock:
            try:
                path = self._storage_path
                os.makedirs(os.path.dirname(path), exist_ok=True)
                
                # FIX: File-level locking to prevent race conditions across multiple worker processes
                # We lock the file itself before writing.
                with open(path, "a") as f_lock:
                    fcntl.flock(f_lock, fcntl.LOCK_EX)
                    try:
                        with open(path, "w") as f:
                            json.dump(self.model_dump(), f, indent=2)
                    finally:
                        fcntl.flock(f_lock, fcntl.LOCK_UN)

                from nexus.memory.supabase_client import get_supabase_client
                sb = get_supabase_client()
                if sb.is_active():
                    sb.ensure_thread_exists(self.session_id)
                    sb.sync_blackboard(self.session_id, self.data)

                self._dirty = False
                logger.info(f"Blackboard | Saved (session: {self.session_id})")
            except Exception as e:
                logger.error(f"Blackboard | Save failed: {e}")

    async def load(self):
        """
        FIX: This method now actually works — called from lifespan in main.py.
        """
        path = self._storage_path
        if not os.path.exists(path):
            return
        try:
            with open(path, "r") as f:
                saved = json.load(f)
            self.data = saved.get("data", {})
            self.history = saved.get("history", [])
            logger.info("Blackboard | Restored session from disk.")
        except Exception as e:
            logger.error(f"Blackboard | Load failed: {e}")

    def get_prompt_context(self) -> str:
        if not self.data:
            return "Blackboard is currently empty."
        ctx = "Current Shared Swarm State:\n"
        for k, v in self.data.items():
            ctx += f"- {k}: {json.dumps(v)[:500]}\n"
        return ctx
