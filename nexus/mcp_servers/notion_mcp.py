"""
notion_mcp.py — Notion MCP (Notion API or Firestore fallback)
"""

from typing import Any


from nexus.config import get_demo_mode, get_notion_token
DEMO_MODE = get_demo_mode()
NOTION_TOKEN = get_notion_token()


NOTION_FIXTURE = [
    {
        "id": "page_1",
        "title": "Python Notes",
        "content": "Python is a high-level programming language...",
    },
    {
        "id": "page_2",
        "title": "Interview Prep",
        "content": "Key topics: Data Structures, Algorithms, System Design...",
    },
]


class NotionMCP:
    """
    Notion integration with Firestore fallback.
    """

    def __init__(self, demo_mode: bool = DEMO_MODE):
        self.demo_mode = demo_mode or DEMO_MODE
        self.token = NOTION_TOKEN
        self._pages: list[dict[str, Any]] = NOTION_FIXTURE.copy() if demo_mode else []

    async def get_pages(self) -> list[dict[str, Any]]:
        """Get all pages from the database."""
        if self.demo_mode:
            return self._pages

        raise NotImplementedError("Real Notion API not implemented")

    async def get_page(self, page_id: str) -> dict[str, Any]:
        """Get a specific page."""
        if self.demo_mode:
            for page in self._pages:
                if page["id"] == page_id:
                    return page
            return {"error": "Page not found"}

        raise NotImplementedError("Real Notion API not implemented")

    async def create_page(self, title: str, content: str) -> dict[str, Any]:
        """Create a new page."""
        if self.demo_mode:
            page = {
                "id": f"page_{len(self._pages) + 1}",
                "title": title,
                "content": content,
            }
            self._pages.append(page)
            return page

        raise NotImplementedError("Real Notion API not implemented")

    async def update_page(
        self, page_id: str, title: str = None, content: str = None
    ) -> dict[str, Any]:
        """Update a page."""
        if self.demo_mode:
            for page in self._pages:
                if page["id"] == page_id:
                    if title:
                        page["title"] = title
                    if content:
                        page["content"] = content
                    return page
            return {"error": "Page not found"}

        raise NotImplementedError("Real Notion API not implemented")
