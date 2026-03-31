"""
supabase_client.py — NEXUS Supabase Persistence Layer (Fixed)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional, List


from nexus.config import get_supabase_url, get_supabase_anon_key, get_supabase_service_role_key

class SupabaseMemoryClient:
    """
    NEXUS Supabase Client for the 4-Layer Memory Hierarchy.

    Table Mapping:
    - Layer 2 (Threads): 'threads' and 'agent_traces'
    - Layer 3 (Context): 'context_items'
    - Layer 4 (Semantic): 'memories' with pgvector
    """

    def __init__(self):
        self.url = get_supabase_url()
        self.key = get_supabase_service_role_key() or get_supabase_anon_key()

        if not self.url or not self.key:
            print("⚠️  Supabase credentials missing. Memory persistence disabled.")
            self.client = None
        else:
            try:
                from supabase import create_client
                self.client = create_client(self.url, self.key)
            except ImportError:
                print("⚠️  supabase package not installed. Memory persistence disabled.")
                self.client = None

    def is_active(self) -> bool:
        return self.client is not None

    # ── Layer 2: Threads & Traces ──────────────────────────────

    def ensure_thread_exists(self, session_id: str) -> None:
        """Idempotent session init — prevents FK violations on trace inserts."""
        if not self.is_active():
            return
        try:
            # FIX: Use datetime ISO string instead of the literal string "now()"
            self.client.table("threads").upsert(
                {
                    "id": session_id,
                    "title": f"NEXUS Session - {session_id[:8]}",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                on_conflict="id",
            ).execute()
        except Exception as e:
            print(f"⚠️  ensure_thread_exists failed: {e}")

    def create_thread(self, title: str, metadata: Optional[dict] = None) -> str:
        if not self.is_active():
            return f"demo_thread_{uuid.uuid4().hex[:8]}"
        try:
            res = (
                self.client.table("threads")
                .insert({"title": title, "metadata": metadata or {}})
                .execute()
            )
            return res.data[0]["id"] if res.data else ""
        except Exception as e:
            print(f"⚠️  create_thread failed: {e}")
            return ""

    def log_trace(
        self, thread_id: str, agent_id: str, status: str, message: str = ""
    ) -> None:
        if not self.is_active():
            return
        try:
            self.client.table("agent_traces").insert(
                {
                    "thread_id": thread_id,
                    "agent_id": agent_id,
                    "status": status,
                    "message": message,
                }
            ).execute()
        except Exception as e:
            # Non-fatal — tracing should never crash the main flow
            print(f"⚠️  log_trace failed: {e}")

    # ── Layer 3: Context / Blackboard ─────────────────────────

    def sync_blackboard(self, session_id: str, data: dict) -> None:
        """Persist entire L3 blackboard as a single context item."""
        if not self.is_active():
            return
        try:
            # FIX: Use datetime ISO string instead of the literal string "now()"
            self.client.table("context_items").upsert(
                {
                    "key": f"blackboard:{session_id}",
                    "value": data,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                on_conflict="key",
            ).execute()
        except Exception as e:
            print(f"⚠️  sync_blackboard failed: {e}")

    def update_context(self, key: str, value: Any) -> None:
        if not self.is_active():
            return
        try:
            # FIX: Use datetime ISO string instead of the literal string "now()"
            self.client.table("context_items").upsert(
                {
                    "key": key,
                    "value": value,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                on_conflict="key",
            ).execute()
        except Exception as e:
            print(f"⚠️  update_context failed: {e}")

    def get_context(self, key: str) -> Optional[Any]:
        if not self.is_active():
            return None
        try:
            res = (
                self.client.table("context_items")
                .select("value")
                .eq("key", key)
                .execute()
            )
            return res.data[0]["value"] if res.data else None
        except Exception as e:
            print(f"⚠️  get_context failed: {e}")
            return None

    # ── Layer 4: Semantic Memories ─────────────────────────────

    async def add_memory(
        self,
        thread_id: str,
        agent_id: str,
        content: str,
        embedding: List[float],
        metadata: Optional[dict] = None,
    ) -> None:
        if not self.is_active():
            return
        try:
            self.client.table("memories").insert(
                {
                    "thread_id": thread_id,
                    "agent_id": agent_id,
                    "content": content,
                    "embedding": embedding,
                    "metadata": metadata or {},
                }
            ).execute()
        except Exception as e:
            print(f"⚠️  add_memory failed: {e}")

    async def search_memories(
        self,
        query_embedding: List[float],
        limit: int = 5,
        match_threshold: float = 0.5,
    ) -> List[dict]:
        """Vector similarity search via Supabase RPC (requires match_memories function)."""
        if not self.is_active():
            return []
        try:
            res = self.client.rpc(
                "match_memories",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": match_threshold,
                    "match_count": limit,
                },
            ).execute()
            return res.data or []
        except Exception as e:
            print(f"⚠️  search_memories failed: {e}")
            return []

    async def get_recent_memories(
        self, limit: int = 20, thread_id: Optional[str] = None
    ) -> List[dict]:
        """
        FIX: Fetch recent memories by created_at instead of empty-query vector search
        which returned nothing because the zero-vector matched no documents.
        """
        if not self.is_active():
            return []
        try:
            query = (
                self.client.table("memories")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
            )
            if thread_id:
                query = query.eq("thread_id", thread_id)
            res = query.execute()
            return res.data or []
        except Exception as e:
            print(f"⚠️  get_recent_memories failed: {e}")
            return []


# ── Global singleton ───────────────────────────────────────────

_client: Optional[SupabaseMemoryClient] = None


def get_supabase_client() -> SupabaseMemoryClient:
    global _client
    if _client is None:
        _client = SupabaseMemoryClient()
    return _client
