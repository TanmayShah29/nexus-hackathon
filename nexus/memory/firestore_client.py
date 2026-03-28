"""
firestore_client.py — Layers 2, 3, 4: Firestore operations

Layer 2: Daily activity log (30-day retention)
Layer 3: Long-term user profile & preferences
Layer 4: Semantic note search (vector stub)

In DEMO_MODE, uses local dict instead of real Firestore.
"""

import os
import time
from datetime import datetime, timedelta
from typing import Any, Optional
from dataclasses import dataclass, field
import json


DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"


@dataclass
class MemoryEntry:
    """A single memory entry stored in any layer."""

    id: str
    user_id: str
    layer: int
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    importance: int = 5
    created_at: float = field(default_factory=time.time)
    tags: list[str] = field(default_factory=list)


class FirestoreClient:
    """
    Multi-layer memory client.

    In demo mode, uses in-memory dicts to simulate Firestore.
    In production, would use firebase-admin SDK.
    """

    def __init__(self, demo_mode: bool = DEMO_MODE):
        self.demo_mode = demo_mode or DEMO_MODE

        if self.demo_mode:
            self._daily_logs: dict[str, list[MemoryEntry]] = {}
            self._user_profiles: dict[str, dict[str, Any]] = {}
            self._notes: dict[str, list[MemoryEntry]] = {}

    def write_daily_log(
        self, user_id: str, activity: str, metadata: Optional[dict] = None
    ) -> str:
        """Layer 2: Write to daily activity log."""
        entry = MemoryEntry(
            id=f"log_{user_id}_{int(time.time())}",
            user_id=user_id,
            layer=2,
            content=activity,
            metadata=metadata or {},
        )

        if self.demo_mode:
            if user_id not in self._daily_logs:
                self._daily_logs[user_id] = []
            self._daily_logs[user_id].append(entry)
            return entry.id

        raise NotImplementedError("Real Firestore not implemented")

    def get_daily_log(self, user_id: str, days: int = 7) -> list[MemoryEntry]:
        """Layer 2: Get daily activity log (last N days)."""
        if self.demo_mode:
            entries = self._daily_logs.get(user_id, [])
            cutoff = time.time() - (days * 86400)
            return [e for e in entries if e.created_at > cutoff]

        raise NotImplementedError("Real Firestore not implemented")

    def write_user_profile(self, user_id: str, updates: dict[str, Any]) -> None:
        """Layer 3: Write to user profile."""
        if self.demo_mode:
            if user_id not in self._user_profiles:
                self._user_profiles[user_id] = {
                    "preferences": {},
                    "goals": [],
                    "history": [],
                    "created_at": time.time(),
                }
            self._user_profiles[user_id].update(updates)
            return

        raise NotImplementedError("Real Firestore not implemented")

    def get_user_profile(self, user_id: str) -> Optional[dict[str, Any]]:
        """Layer 3: Get user profile."""
        if self.demo_mode:
            return self._user_profiles.get(user_id)

        raise NotImplementedError("Real Firestore not implemented")

    def update_preference(self, user_id: str, key: str, value: Any) -> None:
        """Layer 3: Update a single preference."""
        if self.demo_mode:
            if user_id not in self._user_profiles:
                self._user_profiles[user_id] = {"preferences": {}}
            if "preferences" not in self._user_profiles[user_id]:
                self._user_profiles[user_id]["preferences"] = {}
            self._user_profiles[user_id]["preferences"][key] = value
            return

        raise NotImplementedError("Real Firestore not implemented")

    def get_preference(self, user_id: str, key: str, default: Any = None) -> Any:
        """Layer 3: Get a preference."""
        if self.demo_mode:
            profile = self._user_profiles.get(user_id, {})
            return profile.get("preferences", {}).get(key, default)

        raise NotImplementedError("Real Firestore not implemented")

    def write_note(
        self,
        user_id: str,
        content: str,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """Layer 4: Write a note for semantic search."""
        entry = MemoryEntry(
            id=f"note_{user_id}_{int(time.time())}",
            user_id=user_id,
            layer=4,
            content=content,
            tags=tags or [],
            metadata=metadata or {},
            importance=5,
        )

        if self.demo_mode:
            if user_id not in self._notes:
                self._notes[user_id] = []
            self._notes[user_id].append(entry)
            return entry.id

        raise NotImplementedError("Real Firestore not implemented")

    def get_notes(self, user_id: str, limit: int = 50) -> list[MemoryEntry]:
        """Layer 4: Get all notes for a user."""
        if self.demo_mode:
            notes = self._notes.get(user_id, [])
            return sorted(notes, key=lambda x: x.created_at, reverse=True)[:limit]

        raise NotImplementedError("Real Firestore not implemented")

    def search_notes(
        self, user_id: str, query: str, limit: int = 10
    ) -> list[MemoryEntry]:
        """Layer 4: Search notes (simple keyword matching in demo mode)."""
        if self.demo_mode:
            notes = self._notes.get(user_id, [])
            query_lower = query.lower()
            scored = []
            for note in notes:
                score = 0
                if query_lower in note.content.lower():
                    score += 10
                if note.tags:
                    for tag in note.tags:
                        if query_lower in tag.lower():
                            score += 5
                if score > 0:
                    scored.append((score, note))

            scored.sort(key=lambda x: x[0], reverse=True)
            return [n for _, n in scored[:limit]]

        raise NotImplementedError("Real Firestore not implemented")

    def delete_old_logs(self, user_id: str, days: int = 30) -> int:
        """Layer 2: Delete logs older than N days."""
        if self.demo_mode:
            cutoff = time.time() - (days * 86400)
            original_count = len(self._daily_logs.get(user_id, []))
            self._daily_logs[user_id] = [
                e for e in self._daily_logs.get(user_id, []) if e.created_at > cutoff
            ]
            return original_count - len(self._daily_logs[user_id])

        raise NotImplementedError("Real Firestore not implemented")
