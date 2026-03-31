"""
info_mcp.py — Information MCP (Geography + Dictionary)
"""

import logging
from typing import Any, Dict, List
import aiohttp

from nexus.utils.retry import RetryConfig
from nexus.config import get_demo_mode

logger = logging.getLogger("nexus")
DEMO_MODE = get_demo_mode()

INFO_RETRY_CONFIG = RetryConfig(max_attempts=2, base_delay=0.5)

class InfoMCP:
    """
    Geographical data and Dictionary definitions.
    """

    def __init__(self, demo_mode: bool = DEMO_MODE):
        self.demo_mode = demo_mode

    async def get_country_info(self, country_name: str) -> Dict[str, Any]:
        """Fetch country metadata using REST Countries (No Auth)."""
        if self.demo_mode:
            return {"name": country_name, "capital": "New Delhi", "population": 1400000000, "region": "Asia", "status": "demo"}

        url = f"https://restcountries.com/v3.1/name/{country_name}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return {"error": "Country not found."}
                data = await resp.json()
                country = data[0] if isinstance(data, list) else data
                return {
                    "name": country.get("name", {}).get("common"),
                    "capital": country.get("capital", ["Unknown"])[0],
                    "region": country.get("region"),
                    "subregion": country.get("subregion"),
                    "population": country.get("population"),
                    "flag": country.get("flag"),
                    "languages": country.get("languages", {}),
                    "currencies": country.get("currencies", {})
                }

    async def get_definition(self, word: str) -> List[Dict[str, Any]]:
        """Fetch word definition using Free Dictionary API (No Auth)."""
        if self.demo_mode:
            return [{"word": word, "meanings": [{"partOfSpeech": "noun", "definitions": [{"definition": "A placeholder meaning."}]}]}]

        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return [{"error": f"Word '{word}' not found."}]
                return await resp.json()
