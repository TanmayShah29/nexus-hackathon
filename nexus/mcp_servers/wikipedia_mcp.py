"""
wikipedia_mcp.py — Wikipedia MCP (free REST API, no key needed)
"""

from typing import Any
import aiohttp


from nexus.config import get_demo_mode
DEMO_MODE = get_demo_mode()


WIKIPEDIA_FIXTURE = {
    "Python_programming_language": {
        "title": "Python (programming language)",
        "extract": "Python is a high-level, general-purpose programming language that emphasizes code readability with the use of significant indentation.",
        "url": "https://en.wikipedia.org/wiki/Python_(programming_language)",
    }
}


class WikipediaMCP:
    """
    Wikipedia article retrieval using the free REST API.
    """

    def __init__(self, demo_mode: bool = DEMO_MODE):
        self.demo_mode = demo_mode or DEMO_MODE
        self.base_url = "https://en.wikipedia.org/api/rest_v1"

    async def search(self, query: str) -> dict[str, Any]:
        """
        Search Wikipedia for an article.
        Returns {title, extract, url}.
        """
        if self.demo_mode:
            return self._fixture_search(query)

        return await self._wikipedia_search(query)

    def _fixture_search(self, query: str) -> dict[str, Any]:
        """Return fixture data."""
        query_lower = query.lower()
        for key, data in WIKIPEDIA_FIXTURE.items():
            if key.lower() in query_lower or query_lower in key.lower():
                return data
        return {
            "title": query,
            "extract": f"This is a fixture response for '{query}'. In demo mode, Wikipedia search returns cached data.",
            "url": f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}",
        }

    async def _wikipedia_search(self, query: str) -> dict[str, Any]:
        """Search Wikipedia using the REST API."""
        search_url = f"{self.base_url}/page/summary/{query.replace(' ', '_')}"

        async with aiohttp.ClientSession() as session:
            async with session.get(search_url) as resp:
                if resp.status != 200:
                    return self._fixture_search(query)
                data = await resp.json()
                return {
                    "title": data.get("title", query),
                    "extract": data.get("extract", ""),
                    "url": data.get("content_urls", {})
                    .get("desktop", {})
                    .get("page", ""),
                }

    async def get_article(self, title: str) -> dict[str, Any]:
        """Get full article content."""
        if self.demo_mode:
            return self._fixture_search(title)

        return await self._wikipedia_search(title)

    async def search_related(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Get related articles."""
        search_url = f"{self.base_url}/page/related/{query.replace(' ', '_')}"

        async with aiohttp.ClientSession() as session:
            async with session.get(search_url) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                return [
                    {
                        "title": p.get("title", ""),
                        "extract": p.get("extract", ""),
                        "url": p.get("content_urls", {})
                        .get("desktop", {})
                        .get("page", ""),
                    }
                    for p in data.get("pages", [])[:limit]
                ]
