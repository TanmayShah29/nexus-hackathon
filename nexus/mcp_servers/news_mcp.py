"""
news_mcp.py — News MCP (HackerNews + Top Headlines)
"""

import logging
from typing import Any, Dict, List
import aiohttp

from nexus.utils.retry import RetryConfig
from nexus.config import get_demo_mode

logger = logging.getLogger("nexus")
DEMO_MODE = get_demo_mode()

NEWS_RETRY_CONFIG = RetryConfig(max_attempts=2, base_delay=0.5)

class NewsMCP:
    """
    Trending news and top headlines.
    """

    def __init__(self, demo_mode: bool = DEMO_MODE):
        self.demo_mode = demo_mode

    async def get_tech_trends(self, query: str = "AI") -> List[Dict[str, Any]]:
        """Fetch tech trends using HackerNews Algolia API (No Auth)."""
        if self.demo_mode:
            return [{"title": "Democratizing Agentic AI", "url": "https://example.com/ai", "author": "nexus", "points": 450}]

        url = f"https://hn.algolia.com/api/v1/search?query={query}&tags=story"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return [{"error": "HackerNews API Unavailable"}]
                data = await resp.json()
                hits = data.get("hits", [])
                return [
                    {
                        "title": hit.get("title"),
                        "url": hit.get("url"),
                        "author": hit.get("author"),
                        "points": hit.get("points"),
                        "created_at": hit.get("created_at")
                    } for hit in hits[:5] # Return top 5
                ]

    async def get_top_headlines(self, category: str = "business") -> List[Dict[str, Any]]:
        """Mocked top headlines for current category."""
        return [
            {"title": f"Market rally in {category} sector continues", "source": "Finance News", "summary": "NEXUS monitors global trends."},
            {"title": "Breakthrough in Multi-Agent systems", "source": "Tech Journal", "summary": "Swarm intelligence reaches new levels."}
        ]
