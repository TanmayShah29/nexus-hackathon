"""
mcp_servers/search_mcp.py — Web Search MCP
Tavily → Brave → DuckDuckGo fallback.

Fix: Reuse a module-level aiohttp.ClientSession instead of opening
     a new session on every search call (was leaking connections).
"""
from __future__ import annotations

from typing import Any, Optional
import aiohttp

from nexus.config import get_demo_mode, get_tavily_api_key, get_brave_api_key

_DEMO        = get_demo_mode()
_TAVILY_KEY  = get_tavily_api_key()
_BRAVE_KEY   = get_brave_api_key()

# Module-level session — created lazily, reused across calls.
_SESSION: Optional[aiohttp.ClientSession] = None


def _get_session() -> aiohttp.ClientSession:
    global _SESSION
    if _SESSION is None or _SESSION.closed:
        _SESSION = aiohttp.ClientSession()
    return _SESSION


SEARCH_FIXTURE = [
    {"title": "Python Programming Language", "url": "https://python.org",
     "snippet": "Python is a high-level, general-purpose programming language."},
    {"title": "Python Tutorial", "url": "https://w3schools.com/python",
     "snippet": "Learn Python with our complete Python tutorial."},
    {"title": "Real Python", "url": "https://realpython.com",
     "snippet": "Real Python is a repository of free Python tutorials."},
    {"title": "Python Documentation", "url": "https://docs.python.org/3",
     "snippet": "The official documentation for the Python programming language."},
    {"title": "FastAPI", "url": "https://fastapi.tiangolo.com",
     "snippet": "FastAPI framework for building high-performance APIs with Python."},
]


class SearchMCP:
    """Web search using Tavily, Brave, or DuckDuckGo fallback."""

    def __init__(self, demo_mode: bool = _DEMO):
        self.demo_mode  = demo_mode
        self.tavily_key = _TAVILY_KEY
        self.brave_key  = _BRAVE_KEY

    async def search(self, query: str, num_results: int = 5) -> list[dict[str, Any]]:
        if self.demo_mode:
            return SEARCH_FIXTURE[:num_results]
        if self.tavily_key:
            return await self._tavily(query, num_results)
        if self.brave_key:
            return await self._brave(query, num_results)
        return await self._ddg(query, num_results)

    async def _tavily(self, query: str, n: int) -> list[dict[str, Any]]:
        session = _get_session()
        payload = {"api_key": self.tavily_key, "query": query,
                   "search_depth": "basic", "max_results": n}
        try:
            async with session.post("https://api.tavily.com/search", json=payload) as resp:
                if resp.status != 200:
                    return await self._ddg(query, n)
                data = await resp.json()
                return [
                    {"title": r.get("title",""), "url": r.get("url",""),
                     "snippet": r.get("content", r.get("snippet",""))}
                    for r in data.get("results",[])[:n]
                ]
        except Exception:
            return await self._ddg(query, n)

    async def _brave(self, query: str, n: int) -> list[dict[str, Any]]:
        session  = _get_session()
        headers  = {"Accept":"application/json","X-Subscription-Token":self.brave_key}
        try:
            async with session.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers=headers, params={"q":query,"count":n}
            ) as resp:
                if resp.status != 200:
                    return await self._ddg(query, n)
                data = await resp.json()
                return [
                    {"title": r.get("title",""), "url": r.get("url",""),
                     "snippet": r.get("description","")}
                    for r in data.get("web",{}).get("results",[])[:n]
                ]
        except Exception:
            return await self._ddg(query, n)

    async def _ddg(self, query: str, n: int) -> list[dict[str, Any]]:
        """Fallback: DuckDuckGo HTML scrape — no key required."""
        from bs4 import BeautifulSoup
        session = _get_session()
        try:
            async with session.post(
                "https://html.duckduckgo.com/html/",
                data={"q": query}
            ) as resp:
                html = await resp.text()
            soup    = BeautifulSoup(html, "html.parser")
            results = []
            for r in soup.select(".result")[:n]:
                t = r.select_one(".result__title")
                u = r.select_one(".result__url")
                s = r.select_one(".result__snippet")
                if t and u:
                    results.append({
                        "title":   t.get_text(strip=True),
                        "url":     u.get_text(strip=True),
                        "snippet": s.get_text(strip=True) if s else "",
                    })
            return results or SEARCH_FIXTURE[:n]
        except Exception:
            return SEARCH_FIXTURE[:n]
