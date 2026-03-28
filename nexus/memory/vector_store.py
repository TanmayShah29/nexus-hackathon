"""
vector_store.py — Layer 4: Semantic note search

Simple keyword-based search in DEMO_MODE.
In production, would use Pinecone / Chroma / Vertex AI vector search.
"""

import os
import re
from typing import Any, Optional
from collections import defaultdict


DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"


class VectorStore:
    """
    Layer 4 semantic search.

    In DEMO_MODE: simple inverted index + keyword matching.
    In production: vector embeddings via Vertex AI or Pinecone.
    """

    def __init__(self, demo_mode: bool = DEMO_MODE):
        self.demo_mode = demo_mode or DEMO_MODE

        if self.demo_mode:
            self._documents: dict[str, dict[str, Any]] = {}
            self._inverted_index: dict[str, set[str]] = defaultdict(set)

    def add_document(
        self, doc_id: str, content: str, metadata: Optional[dict[str, Any]] = None
    ) -> None:
        """Add a document for semantic search."""
        if self.demo_mode:
            self._documents[doc_id] = {
                "content": content,
                "metadata": metadata or {},
            }

            words = self._tokenize(content)
            for word in words:
                self._inverted_index[word].add(doc_id)
            return

        raise NotImplementedError("Real vector store not implemented")

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Search for documents similar to query."""
        if self.demo_mode:
            query_words = self._tokenize(query)
            if not query_words:
                return []

            doc_scores: dict[str, float] = defaultdict(float)
            for word in query_words:
                for doc_id in self._inverted_index.get(word, set()):
                    doc_scores[doc_id] += 1

            if not doc_scores:
                return []

            sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)

            results = []
            for doc_id, score in sorted_docs[:top_k]:
                doc = self._documents[doc_id]
                results.append(
                    {
                        "doc_id": doc_id,
                        "content": doc["content"],
                        "metadata": doc["metadata"],
                        "score": score,
                    }
                )

            return results

        raise NotImplementedError("Real vector store not implemented")

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document."""
        if self.demo_mode:
            if doc_id in self._documents:
                content = self._documents[doc_id]["content"]
                words = self._tokenize(content)
                for word in words:
                    self._inverted_index[word].discard(doc_id)
                del self._documents[doc_id]
                return True
            return False

        raise NotImplementedError("Real vector store not implemented")

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization."""
        text = text.lower()
        words = re.findall(r"\b\w+\b", text)
        return [w for w in words if len(w) > 2]

    def __repr__(self) -> str:
        return f"VectorStore(demo={self.demo_mode}, docs={len(self._documents)})"
