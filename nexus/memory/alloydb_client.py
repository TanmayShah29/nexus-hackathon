"""
memory/alloydb_client.py — NEXUS AlloyDB AI Persistence Layer

Replaces the Supabase client with a direct psycopg2 connection to
AlloyDB (PostgreSQL-compatible). Uses pgvector for L4 semantic search.

Connection strategy
───────────────────
Cloud Run → AlloyDB via one of two paths:
  1. Cloud SQL Auth Proxy (recommended):  DB_IP is 127.0.0.1, the proxy
     sidecar handles IAM auth automatically.
  2. Direct private IP via VPC connector:  DB_IP is the AlloyDB private IP;
     requires DB_PASS to be set (fetched from Secret Manager at startup).

The client is intentionally synchronous for all L2/L3 calls (DDL, traces,
blackboard) and async only for L4 (embedding inserts + vector search),
matching the calling patterns in the codebase.

Environment variables (see .env.example.gcp)
─────────────────────────────────────────────
  DB_HOST   — AlloyDB private IP or 127.0.0.1 when using Auth Proxy
  DB_PORT   — 5432 (default)
  DB_NAME   — nexus (or your database name)
  DB_USER   — nexus_user (or IAM service-account email for IAM auth)
  DB_PASS   — password; leave empty when using the Cloud SQL Auth Proxy
              with IAM authentication
  DB_POOL_MIN  — minimum connections in pool (default 2)
  DB_POOL_MAX  — maximum connections in pool (default 10)
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional

logger = logging.getLogger("nexus")

# ---------------------------------------------------------------------------
# psycopg2 + connection pool
# ---------------------------------------------------------------------------
try:
    import psycopg2
    import psycopg2.pool
    import psycopg2.extras  # for RealDictCursor and Json adapter
    _PSYCOPG2_AVAILABLE = True
except ImportError:
    _PSYCOPG2_AVAILABLE = False
    logger.warning("psycopg2 not installed — AlloyDB persistence disabled.")


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


class AlloyDBClient:
    """
    NEXUS AlloyDB client — drop-in replacement for SupabaseMemoryClient.

    Public interface is identical so callers (blackboard, agent_tracer,
    vector_store, routes/memory) need zero changes.
    """

    def __init__(self) -> None:
        self._pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None
        self._active = False

        if not _PSYCOPG2_AVAILABLE:
            return

        host = _env("DB_HOST")
        port = int(_env("DB_PORT", "5432"))
        dbname = _env("DB_NAME", "nexus")
        user = _env("DB_USER")
        password = _env("DB_PASS", "")  # empty when using Auth Proxy IAM auth
        min_conn = int(_env("DB_POOL_MIN", "2"))
        max_conn = int(_env("DB_POOL_MAX", "10"))

        if not host or not user:
            logger.warning(
                "AlloyDB: DB_HOST or DB_USER not set — persistence disabled."
            )
            return

        try:
            conn_kwargs: dict[str, Any] = {
                "host": host,
                "port": port,
                "dbname": dbname,
                "user": user,
                "connect_timeout": 10,
                # cursor_factory set per-connection below
            }
            if password:
                conn_kwargs["password"] = password

            self._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=min_conn,
                maxconn=max_conn,
                **conn_kwargs,
            )
            self._active = True
            logger.info(
                f"AlloyDB: connected to {host}:{port}/{dbname} "
                f"(pool {min_conn}–{max_conn})"
            )
        except Exception as exc:
            logger.error(f"AlloyDB: connection pool creation failed — {exc}")

    # ── Connection helpers ─────────────────────────────────────

    def is_active(self) -> bool:
        return self._active and self._pool is not None

    def _conn(self):
        """Get a connection from the pool. Caller must call _put(conn)."""
        if not self.is_active():
            raise RuntimeError("AlloyDB pool not available")
        conn = self._pool.getconn()
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        return conn

    def _put(self, conn) -> None:
        if self._pool and conn:
            self._pool.putconn(conn)

    def _execute(self, sql: str, params: tuple = (), fetch: str = "none") -> Any:
        """
        Thread-safe query helper.
        fetch: 'none' | 'one' | 'all'
        """
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                conn.commit()
                if fetch == "one":
                    return dict(cur.fetchone()) if cur.rowcount != 0 else None
                if fetch == "all":
                    rows = cur.fetchall()
                    return [dict(r) for r in rows]
                return None
        except Exception as exc:
            conn.rollback()
            logger.error(f"AlloyDB query failed: {exc}\nSQL: {sql}")
            raise
        finally:
            self._put(conn)

    # ── Layer 2: Threads ──────────────────────────────────────

    def ensure_thread_exists(self, session_id: str) -> None:
        """Idempotent upsert — prevents FK violations on trace inserts."""
        if not self.is_active():
            return
        try:
            self._execute(
                """
                INSERT INTO threads (id, title, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (id) DO UPDATE
                    SET updated_at = NOW()
                """,
                (session_id, f"NEXUS Session - {session_id[:8]}"),
            )
        except Exception as exc:
            logger.warning(f"ensure_thread_exists failed: {exc}")

    def create_thread(self, title: str, metadata: Optional[dict] = None) -> str:
        if not self.is_active():
            return f"demo_thread_{uuid.uuid4().hex[:8]}"
        try:
            row = self._execute(
                """
                INSERT INTO threads (id, title, metadata)
                VALUES (gen_random_uuid()::TEXT, %s, %s)
                RETURNING id
                """,
                (title, json.dumps(metadata or {})),
                fetch="one",
            )
            return row["id"] if row else ""
        except Exception as exc:
            logger.warning(f"create_thread failed: {exc}")
            return ""

    def log_trace(
        self, thread_id: str, agent_id: str, status: str, message: str = ""
    ) -> None:
        if not self.is_active():
            return
        try:
            # Ensure thread exists to avoid FK violation (fire-and-forget)
            self.ensure_thread_exists(thread_id)
            self._execute(
                """
                INSERT INTO agent_traces (thread_id, agent_id, status, message)
                VALUES (%s, %s, %s, %s)
                """,
                (thread_id, agent_id, status, message),
            )
        except Exception as exc:
            # Tracing is non-fatal
            logger.debug(f"log_trace failed (non-fatal): {exc}")

    # ── Layer 3: Context / Blackboard ─────────────────────────

    def sync_blackboard(self, session_id: str, data: dict) -> None:
        if not self.is_active():
            return
        try:
            self._execute(
                """
                INSERT INTO context_items (key, value, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (key) DO UPDATE
                    SET value = EXCLUDED.value,
                        updated_at = NOW()
                """,
                (f"blackboard:{session_id}", json.dumps(data)),
            )
        except Exception as exc:
            logger.warning(f"sync_blackboard failed: {exc}")

    def update_context(self, key: str, value: Any) -> None:
        if not self.is_active():
            return
        try:
            self._execute(
                """
                INSERT INTO context_items (key, value, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (key) DO UPDATE
                    SET value = EXCLUDED.value,
                        updated_at = NOW()
                """,
                (key, json.dumps(value)),
            )
        except Exception as exc:
            logger.warning(f"update_context failed: {exc}")

    def get_context(self, key: str) -> Optional[Any]:
        if not self.is_active():
            return None
        try:
            row = self._execute(
                "SELECT value FROM context_items WHERE key = %s",
                (key,),
                fetch="one",
            )
            if row and row.get("value") is not None:
                v = row["value"]
                # psycopg2 JSONB columns come back as dict/list already
                return v if not isinstance(v, str) else json.loads(v)
            return None
        except Exception as exc:
            logger.warning(f"get_context failed: {exc}")
            return None

    # ── Layer 4: Semantic Memories (async wrappers) ────────────
    #
    # These are async because VectorStore.add_document / search are async.
    # The underlying psycopg2 calls are synchronous — they run on the
    # default thread pool via asyncio.to_thread so they never block the
    # event loop.

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
        import asyncio
        await asyncio.to_thread(
            self._add_memory_sync,
            thread_id, agent_id, content, embedding, metadata
        )

    def _add_memory_sync(
        self,
        thread_id: str,
        agent_id: str,
        content: str,
        embedding: List[float],
        metadata: Optional[dict],
    ) -> None:
        try:
            self.ensure_thread_exists(thread_id)
            # pgvector expects a Python list; psycopg2 serialises it correctly
            self._execute(
                """
                INSERT INTO memories (thread_id, agent_id, content, embedding, metadata)
                VALUES (%s, %s, %s, %s::vector, %s)
                """,
                (
                    thread_id,
                    agent_id,
                    content,
                    str(embedding),          # '[0.1, 0.2, ...]' — psycopg2 cast to vector
                    json.dumps(metadata or {}),
                ),
            )
        except Exception as exc:
            logger.warning(f"add_memory failed: {exc}")

    async def search_memories(
        self,
        query_embedding: List[float],
        limit: int = 5,
        match_threshold: float = 0.5,
    ) -> List[dict]:
        """Cosine similarity search via the match_memories() SQL function."""
        if not self.is_active():
            return []
        import asyncio
        return await asyncio.to_thread(
            self._search_memories_sync, query_embedding, limit, match_threshold
        )

    def _search_memories_sync(
        self,
        query_embedding: List[float],
        limit: int,
        match_threshold: float,
    ) -> List[dict]:
        try:
            rows = self._execute(
                "SELECT * FROM match_memories(%s::vector, %s, %s)",
                (str(query_embedding), match_threshold, limit),
                fetch="all",
            )
            return rows or []
        except Exception as exc:
            logger.warning(f"search_memories failed: {exc}")
            return []

    async def get_recent_memories(
        self, limit: int = 20, thread_id: Optional[str] = None
    ) -> List[dict]:
        """Return most-recent memory rows (for dashboard / empty-query)."""
        if not self.is_active():
            return []
        import asyncio
        return await asyncio.to_thread(
            self._get_recent_memories_sync, limit, thread_id
        )

    def _get_recent_memories_sync(
        self, limit: int, thread_id: Optional[str]
    ) -> List[dict]:
        try:
            if thread_id:
                rows = self._execute(
                    """
                    SELECT id, thread_id, agent_id, content, metadata, created_at
                    FROM memories
                    WHERE thread_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (thread_id, limit),
                    fetch="all",
                )
            else:
                rows = self._execute(
                    """
                    SELECT id, thread_id, agent_id, content, metadata, created_at
                    FROM memories
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                    fetch="all",
                )
            # Normalise metadata to dict (comes back as dict from JSONB)
            result = []
            for r in (rows or []):
                r = dict(r)
                r["id"] = str(r["id"])  # UUID → str
                if isinstance(r.get("metadata"), str):
                    r["metadata"] = json.loads(r["metadata"])
                result.append(r)
            return result
        except Exception as exc:
            logger.warning(f"get_recent_memories failed: {exc}")
            return []

    # ── Cleanup ────────────────────────────────────────────────

    def close(self) -> None:
        if self._pool:
            self._pool.closeall()
            self._active = False
            logger.info("AlloyDB: connection pool closed.")


# ── Global singleton ───────────────────────────────────────────

_client: Optional[AlloyDBClient] = None


def get_db_client() -> AlloyDBClient:
    """
    Return the module-level AlloyDB singleton.
    This is the new canonical entry-point — it replaces get_supabase_client().
    """
    global _client
    if _client is None:
        _client = AlloyDBClient()
    return _client


# ---------------------------------------------------------------------------
# Backwards-compat shim
# ---------------------------------------------------------------------------
# All existing callers import get_supabase_client.  Aliasing here means
# we only need to change this one file — no grep-and-replace across the repo.
def get_supabase_client() -> AlloyDBClient:
    return get_db_client()
