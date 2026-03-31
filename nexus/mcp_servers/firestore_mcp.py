"""
firestore_mcp.py — Firestore MCP (In-memory operations)
Connected to NEXUS Multi-Layer Memory
"""

from typing import Any, Optional
from nexus.config import get_demo_mode

DEMO_MODE = get_demo_mode()


class FirestoreMCP:
    """
    Firestore-like CRUD operations using in-memory storage.
    """

    def __init__(self, demo_mode: bool = DEMO_MODE, user_id: str = "default"):
        self.demo_mode = demo_mode or DEMO_MODE
        self.user_id = user_id
        self._notes = {}
        self._tasks = {}

    async def write_document(
        self, collection: str, document_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Write a document (Unified helper for Notes and Tasks)."""
        user_id = data.get("user_id", self.user_id)

        if collection == "notes":
            self._notes[document_id] = {
                "id": document_id,
                "content": data.get("content", ""),
                "tags": data.get("tags", []),
                "metadata": data,
                "user_id": user_id,
            }
        elif collection == "tasks":
            self._tasks[document_id] = {
                "id": document_id,
                "title": data.get("title", "New Task"),
                "description": data.get("description", ""),
                "priority": data.get("priority", "medium"),
                "due_date": data.get("due_date"),
                "status": data.get("status", "pending"),
                "user_id": user_id,
            }

        return {
            "collection": collection,
            "document_id": document_id,
            "status": "success",
            "storage_layer": "semantic" if collection == "notes" else "relational",
        }

    async def create(
        self, collection: str, document_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a document."""
        return await self.write_document(collection, document_id, data)

    async def read(self, collection: str, document_id: str) -> dict[str, Any]:
        """Read a document."""
        if collection == "notes":
            note = self._notes.get(document_id)
            if note:
                return {"content": note["content"], **note.get("metadata", {})}
        elif collection == "tasks":
            task = self._tasks.get(document_id)
            if task and task.get("user_id") == self.user_id:
                return task

        return {"error": "Not found or collection not supported for direct read"}

    async def update(
        self, collection: str, document_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a document."""
        if collection == "tasks":
            if document_id in self._tasks:
                self._tasks[document_id].update(data)
            return {"status": "updated"}
        return {"error": "Update only supported for tasks in this MCP"}

    async def delete(self, collection: str, document_id: str) -> dict[str, Any]:
        """Delete a document."""
        if collection == "tasks":
            if document_id in self._tasks:
                del self._tasks[document_id]
            return {"status": "deleted"}
        return {"error": "Delete only supported for tasks in this MCP"}

    async def query(
        self, collection: str, field: str, operator: str, value: Optional[Any] = None
    ) -> list[dict[str, Any]]:
        """Query documents."""
        if collection == "notes":
            results = []
            query_value = value if value is not None else operator
            for note in self._notes.values():
                if query_value.lower() in note.get("content", "").lower():
                    results.append(
                        {
                            "document_id": note["id"],
                            "content": note["content"],
                            **note.get("metadata", {}),
                        }
                    )
            return results

        elif collection == "tasks":
            status_filter = value if field == "status" else None
            tasks = [
                t for t in self._tasks.values() if t.get("user_id") == self.user_id
            ]
            if status_filter:
                tasks = [t for t in tasks if t.get("status") == status_filter]
            return tasks

        return []
