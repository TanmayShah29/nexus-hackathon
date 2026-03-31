import aiohttp
import logging
from typing import Any, Dict

logger = logging.getLogger("nexus")

class HealthMCP:
    """
    MCP Server for Health, Nutrition, and Well-being.
    """

    async def get_activity_suggestion(self, type: str = None) -> Dict[str, Any]:
        """Returns a random cognitive or physical activity suggestion for a mental break."""
        url = "https://www.boredapi.com/api/activity"
        if type:
            url += f"?type={type}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return {"error": f"Bored API returned {resp.status}"}
        except Exception as e:
            logger.error(f"HealthMCP | Bored call failed: {e}")
            return {"error": str(e)}

    async def search_nutrition(self, query: str) -> Dict[str, Any]:
        """Searches the USDA FoodData Central database for nutritional information."""
        # Using DEMO_KEY limit.
        url = f"https://api.nal.usda.gov/fdc/v1/foods/search?api_key=DEMO_KEY&query={query}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return {"error": f"USDA API returned {resp.status}"}
        except Exception as e:
            logger.error(f"HealthMCP | USDA call failed: {e}")
            return {"error": str(e)}
