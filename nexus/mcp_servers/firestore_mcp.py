"""
firestore_mcp.py — Firestore MCP (CRUD operations)
"""

import os
from typing import Any
from datetime import datetime


DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"


class FirestoreMCP:
    """
    Firestore CRUD operations.
    """

    def __init__(self, demo_mode: bool = DEMO_MODE):
        self.demo_mode = demo_mode or DEMO_MODE
        self._data: dict[str, dict[str, Any]] = {}

    async def create(
        self, collection: str, document_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a document."""
        if self.demo_mode:
            key = f"{collection}/{document_id}"
            self._data[key] = data
            return {
                "collection": collection,
                "document_id": document_id,
                "status": "created",
            }

        raise NotImplementedError("Real Firestore not implemented")

    async def read(self, collection: str, document_id: str) -> dict[str, Any]:
        """Read a document."""
        if self.demo_mode:
            key = f"{collection}/{document_id}"
            return self._data.get(key, {"error": "Not found"})

        raise NotImplementedError("Real Firestore not implemented")

    async def update(
        self, collection: str, document_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a document."""
        if self.demo_mode:
            key = f"{collection}/{document_id}"
            if key in self._data:
                self._data[key].update(data)
                return {
                    "collection": collection,
                    "document_id": document_id,
                    "status": "updated",
                }
            return {"error": "Document not found"}

        raise NotImplementedError("Real Firestore not implemented")

    async def delete(self, collection: str, document_id: str) -> dict[str, Any]:
        """Delete a document."""
        if self.demo_mode:
            key = f"{collection}/{document_id}"
            if key in self._data:
                del self._data[key]
                return {
                    "collection": collection,
                    "document_id": document_id,
                    "status": "deleted",
                }
            return {"error": "Not found"}

        raise NotImplementedError("Real Firestore not implemented")

    async def query(
        self, collection: str, field: str, operator: str, value: Any
    ) -> list[dict[str, Any]]:
        """Query documents."""
        if self.demo_mode:
            results = []
            prefix = f"{collection}/"
            for key, doc in self._data.items():
                if key.startswith(prefix) and field in doc:
                    if operator == "==" and doc[field] == value:
                        results.append({"document_id": key.replace(prefix, ""), **doc})
            return results

        raise NotImplementedError("Real Firestore not implemented")
