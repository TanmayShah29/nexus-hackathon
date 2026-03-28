"""
session_cache.py — Layer 1: In-memory session state cache

Fast, temporary storage for the current session.
Lives only as long as the session is active.
"""

import time
from typing import Any, Optional
from threading import Lock


class SessionCache:
    """
    Layer 1 memory: in-memory session state.

    Each session gets its own isolated dict.
    Thread-safe for concurrent access.
    """

    def __init__(self, session_id: str, ttl_seconds: int = 3600):
        self.session_id = session_id
        self.ttl_seconds = ttl_seconds
        self._data: dict[str, Any] = {}
        self._created_at = time.time()
        self._lock = Lock()

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def has(self, key: str) -> bool:
        with self._lock:
            return key in self._data

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def keys(self) -> list[str]:
        with self._lock:
            return list(self._data.keys())

    def items(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._data)

    def is_expired(self) -> bool:
        return time.time() - self._created_at > self.ttl_seconds

    def __repr__(self) -> str:
        return f"SessionCache(session_id={self.session_id}, keys={list(self._data.keys())})"


class SessionCacheStore:
    """
    Global store for all active sessions.
    """

    def __init__(self):
        self._sessions: dict[str, SessionCache] = {}
        self._lock = Lock()

    def create(self, session_id: str, ttl_seconds: int = 3600) -> SessionCache:
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionCache(session_id, ttl_seconds)
            return self._sessions[session_id]

    def get(self, session_id: str) -> Optional[SessionCache]:
        with self._lock:
            return self._sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    def cleanup_expired(self) -> int:
        """Remove expired sessions. Returns count of removed sessions."""
        removed = 0
        with self._lock:
            expired = [
                sid for sid, cache in self._sessions.items() if cache.is_expired()
            ]
            for sid in expired:
                del self._sessions[sid]
                removed += 1
        return removed

    def __repr__(self) -> str:
        return f"SessionCacheStore(sessions={len(self._sessions)})"


session_store = SessionCacheStore()
