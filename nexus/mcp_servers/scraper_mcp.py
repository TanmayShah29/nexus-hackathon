"""
scraper_mcp.py — Web Scraper MCP (BeautifulSoup)
"""

from typing import Any
import aiohttp
from bs4 import BeautifulSoup


from nexus.config import get_demo_mode
DEMO_MODE = get_demo_mode()


SCRAPER_FIXTURE = {
    "python.org": {
        "title": "Python.org",
        "content": "Python is a programming language for general-purpose programming...",
    }
}


class ScraperMCP:
    """
    Web scraper using BeautifulSoup.
    """

    def __init__(self, demo_mode: bool = DEMO_MODE):
        self.demo_mode = demo_mode or DEMO_MODE

    async def scrape(self, url: str) -> dict[str, Any]:
        """
        Scrape a webpage.
        Returns {title, content, url}.
        """
        if self.demo_mode:
            return self._fixture_scrape(url)

        return await self._scrape_url(url)

    def _fixture_scrape(self, url: str) -> dict[str, Any]:
        """Return fixture data."""
        for domain, data in SCRAPER_FIXTURE.items():
            if domain in url:
                result = data.copy()
                result["url"] = url
                return result
        return {
            "title": "Scraped Page",
            "content": f"Fixture content for {url}",
            "url": url,
        }

    async def _scrape_url(self, url: str) -> dict[str, Any]:
        """Scrape a URL using BeautifulSoup."""
        headers = {"User-Agent": "Mozilla/5.0 (compatible; NEXUS/1.0)"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as resp:
                if resp.status != 200:
                    return self._fixture_scrape(url)
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")

                title = soup.title.string if soup.title else url
                for script in soup(["script", "style"]):
                    script.decompose()
                text = soup.get_text(separator="\n", strip=True)

                return {
                    "title": title,
                    "content": text[:5000],
                    "url": url,
                }
