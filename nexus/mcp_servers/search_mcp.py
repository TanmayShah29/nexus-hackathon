"""
search_mcp.py — Web Search MCP (Tavily + Brave + DuckDuckGo fallback)
"""

import os
import asyncio
from typing import Any, Optional
import aiohttp


DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")


SEARCH_FIXTURE = [
    {
        "title": "Python Programming Language",
        "url": "https://python.org",
        "snippet": "Python is a high-level, general-purpose programming language.",
    },
    {
        "title": "Python Tutorial",
        "url": "https://w3schools.com/python",
        "snippet": "Learn Python with our complete Python tutorial.",
    },
    {
        "title": "Python for Beginners",
        "url": "https://realpython.com",
        "snippet": "Real Python is a repository of free Python tutorials.",
    },
    {
        "title": "Python Documentation",
        "url": "https://docs.python.org/3",
        "snippet": "The official documentation for Python programming language.",
    },
    {
        "title": "Python FastAPI",
        "url": "https://fastapi.tiangolo.com",
        "snippet": "FastAPI framework for building APIs with Python.",
    },
]


class SearchMCP:
    """
    Web search using Tavily, Brave, or DuckDuckGo fallback.
    """

    def __init__(self, demo_mode: bool = DEMO_MODE):
        self.demo_mode = demo_mode or DEMO_MODE
        self.tavily_key = TAVILY_API_KEY
        self.brave_key = BRAVE_API_KEY

    async def search(self, query: str, num_results: int = 5) -> list[dict[str, Any]]:
        """
        Search the web for the given query.
        Returns list of {title, url, snippet}.
        """
        if self.demo_mode:
            return self._fixture_search(query, num_results)

        if self.tavily_key:
            return await self._tavily_search(query, num_results)
        elif self.brave_key:
            return await self._brave_search(query, num_results)
        else:
            return await self._ddg_search(query, num_results)

    def _fixture_search(self, query: str, num_results: int) -> list[dict[str, Any]]:
        """Return fixture data."""
        return SEARCH_FIXTURE[:num_results]

    async def _tavily_search(
        self, query: str, num_results: int
    ) -> list[dict[str, Any]]:
        """Search using Tavily API."""
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.tavily_key,
            "query": query,
            "search_depth": "basic",
            "max_results": num_results,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    return await self._ddg_search(query, num_results)
                data = await resp.json()
                return [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "snippet": r.get("content", r.get("snippet", "")),
                    }
                    for r in data.get("results", [])
                ]

    async def _brave_search(self, query: str, num_results: int) -> list[dict[str, Any]]:
        """Search using Brave API."""
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {"Accept": "application/json", "X-Subscription-Token": self.brave_key}
        params = {"q": query, "count": num_results}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status != 200:
                    return await self._ddg_search(query, num_results)
                data = await resp.json()
                return [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "snippet": r.get("description", ""),
                    }
                    for r in data.get("web", {}).get("results", [])
                ]

    async def _ddg_search(self, query: str, num_results: int) -> list[dict[str, Any]]:
        """Fallback: DuckDuckGo HTML scrape."""
        url = "https://html.duckduckgo.com/html/"
        data = {"q": query, "b": f"1:{num_results}"}

        from bs4 import BeautifulSoup

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")
                results = []
                for result in soup.select(".result")[:num_results]:
                    title_elem = result.select_one(".result__title")
                    url_elem = result.select_one(".result__url")
                    snippet_elem = result.select_one(".result__snippet")
                    if title_elem and url_elem:
                        results.append(
                            {
                                "title": title_elem.get_text(strip=True),
                                "url": url_elem.get_text(strip=True),
                                "snippet": snippet_elem.get_text(strip=True)
                                if snippet_elem
                                else "",
                            }
                        )
                return results if results else SEARCH_FIXTURE[:num_results]
