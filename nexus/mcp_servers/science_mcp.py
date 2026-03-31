import aiohttp
import logging
from typing import Any, Dict

logger = logging.getLogger("nexus")

class ScienceMCP:
    """
    MCP Server for Scientific and Astronomical data.
    """

    async def get_iss_location(self) -> Dict[str, Any]:
        """Returns the current real-time coordinates of the International Space Station."""
        url = "https://api.wheretheiss.at/v1/satellites/25544"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return {"error": f"ISS API returned {resp.status}"}
        except Exception as e:
            logger.error(f"ScienceMCP | ISS track failed: {e}")
            return {"error": str(e)}

    async def get_nasa_apod(self) -> Dict[str, Any]:
        """Returns NASA's Astronomy Picture of the Day (APOD) metadata."""
        # Using DEMO_KEY (publicly available with rate limits)
        url = "https://api.nasa.gov/planetary/apod?api_key=DEMO_KEY"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return {"error": f"NASA APOD returned {resp.status}"}
        except Exception as e:
            logger.error(f"ScienceMCP | NASA APOD failed: {e}")
            return {"error": str(e)}

    async def get_mars_weather(self) -> Dict[str, Any]:
        """Returns the latest weather report from the InSight Mars Lander."""
        url = "https://api.nasa.gov/insight_weather/?api_key=DEMO_KEY&feedtype=json&ver=1.0"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return {"error": f"NASA Mars Weather returned {resp.status}"}
        except Exception as e:
            logger.error(f"ScienceMCP | Mars Weather failed: {e}")
            return {"error": str(e)}
