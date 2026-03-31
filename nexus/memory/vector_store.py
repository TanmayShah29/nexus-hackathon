"""
vector_store.py — Layer 4: Semantic search with JSON persistence (Fixed)
"""
from __future__ import annotations

import os
import math
import json
import uuid  # FIX: uuid was used but never imported
import logging
from typing import Any, Optional, List

from nexus.agents.gemini_client import generate_embedding

logger = logging.getLogger("nexus")


from nexus.config import get_demo_mode as _demo_mode


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    mag1 = math.sqrt(sum(a * a for a in v1))
    mag2 = math.sqrt(sum(b * b for b in v2))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)


class KnowledgeGraph:
    """Relational layer — maps concept connections."""

    def __init__(self):
        self.nodes: dict[str, dict] = {}
        self.edges: list[tuple[str, str, str]] = []

    def add_node(self, node_id: str, label: str, metadata: dict = None):
        self.nodes[node_id] = {"label": label, "metadata": metadata or {}}

    def add_edge(self, source: str, target: str, relation: str):
        if source in self.nodes and target in self.nodes:
            edge = (source, target, relation)
            if edge not in self.edges:
                self.edges.append(edge)

    def get_related(self, node_id: str) -> list[dict]:
        related = []
        for s, t, r in self.edges:
            if s == node_id:
                related.append({"node_id": t, "relation": r, **self.nodes.get(t, {})})
            elif t == node_id:
                related.append({"node_id": s, "relation": r, **self.nodes.get(s, {})})
        return related

    def to_dict(self) -> dict:
        return {"nodes": self.nodes, "edges": self.edges}

    def from_dict(self, data: dict):
        self.nodes = data.get("nodes", {})
        self.edges = [tuple(e) for e in data.get("edges", [])]


class VectorStore:
    """Layer 4 semantic search — Supabase primary, local JSON fallback."""

    def __init__(self, demo_mode: bool = None):
        self.demo_mode = demo_mode if demo_mode is not None else _demo_mode()
        self.kg = KnowledgeGraph()
        self._documents: dict[str, dict[str, Any]] = {}

        # FIX: Import uses package-qualified path
        from nexus.memory.supabase_client import get_supabase_client
        self.sb = get_supabase_client()

        # FIX: Use __file__-relative path instead of a working-directory-relative string
        _base_dir = os.path.dirname(os.path.abspath(__file__))
        self.persist_path = os.path.join(_base_dir, "vector_store.json")
        self.load()

    def save(self):
        """Local JSON fallback — skipped when Supabase is active."""
        if self.sb.is_active():
            return
        try:
            data = {"documents": self._documents, "kg": self.kg.to_dict()}
            with open(self.persist_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"VectorStore.save failed: {e}")

    def load(self):
        if not os.path.exists(self.persist_path):
            return
        try:
            with open(self.persist_path, "r") as f:
                data = json.load(f)
            self._documents = data.get("documents", {})
            self.kg.from_dict(data.get("kg", {}))
            logger.info(f"VectorStore: loaded {len(self._documents)} documents from disk.")
        except Exception as e:
            logger.error(f"VectorStore.load failed: {e}")

    async def add_document(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
        thread_id: Optional[str] = None,
    ) -> None:
        embedding = await generate_embedding(content)
        if not embedding:
            logger.error(f"VectorStore: failed to generate embedding for {doc_id}")
            return

        # FIX: uuid is now imported at the top of this file
        effective_thread_id = thread_id or str(uuid.uuid4())

        if self.sb.is_active():
            await self.sb.add_memory(
                thread_id=effective_thread_id,
                agent_id=(metadata or {}).get("agent", "nexus"),
                content=content,
                embedding=embedding,
                metadata=metadata or {},
            )

        self._documents[doc_id] = {
            "content": content,
            "metadata": metadata or {},
            "embedding": embedding,
        }

        title = (metadata or {}).get("title", "Document")
        self.kg.add_node(doc_id, title, metadata)

        for other_id, other_doc in self._documents.items():
            if other_id == doc_id:
                continue
            if cosine_similarity(embedding, other_doc["embedding"]) > 0.85:
                self.kg.add_edge(doc_id, other_id, "semantically_related")

        self.save()

    async def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        FIX: Empty query now fetches recent memories instead of doing a
        meaningless vector search that always returned nothing.
        """
        # Empty-query shortcut → return recent memories
        if not query.strip():
            return await self._get_recent(top_k)

        query_embedding = await generate_embedding(query)
        if not query_embedding:
            return []

        if self.sb.is_active():
            sb_results = await self.sb.search_memories(query_embedding, limit=top_k)
            return [
                {
                    "doc_id": r.get("id", ""),
                    "content": r.get("content", ""),
                    "metadata": r.get("metadata", {}),
                    "score": round(r.get("similarity", 0.0), 4),
                    "related_insights": self.kg.get_related(r.get("id", ""))[:3],
                }
                for r in sb_results
            ]

        # Local fallback
        scored: list[tuple[str, float]] = []
        for doc_id, doc in self._documents.items():
            score = cosine_similarity(query_embedding, doc["embedding"])
            if score > 0.3:
                scored.append((doc_id, score))
        scored.sort(key=lambda x: x[1], reverse=True)

        return [
            {
                "doc_id": did,
                "content": self._documents[did]["content"],
                "metadata": self._documents[did]["metadata"],
                "score": round(score, 4),
                "related_insights": self.kg.get_related(did)[:3],
            }
            for did, score in scored[:top_k]
        ]

    async def _get_recent(self, top_k: int) -> list[dict[str, Any]]:
        """Return most-recent memories for the memory dashboard."""
        if self.sb.is_active():
            recent = await self.sb.get_recent_memories(limit=top_k)
            return [
                {
                    "doc_id": r.get("id", ""),
                    "content": r.get("content", ""),
                    "metadata": r.get("metadata", {}),
                    "score": 1.0,
                    "related_insights": [],
                }
                for r in recent
            ]

        # Local fallback — return last N documents
        items = list(self._documents.items())[-top_k:]
        return [
            {
                "doc_id": did,
                "content": doc["content"],
                "metadata": doc["metadata"],
                "score": 1.0,
                "related_insights": [],
            }
            for did, doc in reversed(items)
        ]

    def delete_document(self, doc_id: str) -> bool:
        if doc_id in self._documents:
            del self._documents[doc_id]
            self.kg.nodes.pop(doc_id, None)
            self.kg.edges = [e for e in self.kg.edges if e[0] != doc_id and e[1] != doc_id]
            self.save()
            return True
        return False

    def __repr__(self) -> str:
        return f"VectorStore(docs={len(self._documents)})"
