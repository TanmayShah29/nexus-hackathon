import aiohttp
import logging
import random
from typing import Any, Dict

logger = logging.getLogger("nexus")

class CultureMCP:
    """
    MCP Server for Arts, Culture, and Philosophy.
    """

    async def get_random_artwork(self) -> Dict[str, Any]:
        """Returns a random artwork from the Art Institute of Chicago collection."""
        url = "https://api.artic.edu/api/v1/artworks?limit=1&page=" + str(random.randint(1, 100))
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data['data'][0]
                    return {"error": f"Art Institute API returned {resp.status}"}
        except Exception as e:
            logger.error(f"CultureMCP | Art Institute call failed: {e}")
            return {"error": str(e)}

    async def get_quote(self) -> Dict[str, Any]:
        """Returns an inspirational quote for mental priming."""
        url = "https://api.quotable.io/random"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return {"error": f"Quotable API returned {resp.status}"}
        except Exception as e:
            logger.error(f"CultureMCP | Quotable call failed: {e}")
            return {"error": str(e)}

    async def get_museum_object(self, object_id: int) -> Dict[str, Any]:
        """Returns a specific object from the Metropolitan Museum of Art."""
        url = f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{object_id}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return {"error": f"Met Museum API returned {resp.status}"}
        except Exception as e:
            logger.error(f"CultureMCP | Met Museum call failed: {e}")
            return {"error": str(e)}
