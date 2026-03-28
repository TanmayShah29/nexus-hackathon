"""
weather_mcp.py — Weather MCP (OpenWeatherMap + wttr.in fallback)
"""

import os
import asyncio
from typing import Any
import aiohttp


DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")


WEATHER_FIXTURE = {
    "location": "Mumbai",
    "description": "Clear sky",
    "temperature": 28,
    "humidity": 65,
    "wind_speed": 12,
    "icon": "01d",
}


class WeatherMCP:
    """
    Weather data using OpenWeatherMap or wttr.in fallback.
    """

    def __init__(self, demo_mode: bool = DEMO_MODE):
        self.demo_mode = demo_mode or DEMO_MODE
        self.api_key = OPENWEATHER_API_KEY

    async def get_current(self, location: str) -> dict[str, Any]:
        """
        Get current weather for a location.
        Returns {location, description, temperature, humidity, wind_speed, icon}.
        """
        if self.demo_mode:
            return self._fixture_weather(location)

        if self.api_key:
            return await self._openweather(location)
        else:
            return await self._wttr_in(location)

    def _fixture_weather(self, location: str) -> dict[str, Any]:
        """Return fixture data with location updated."""
        data = WEATHER_FIXTURE.copy()
        data["location"] = location
        return data

    async def _openweather(self, location: str) -> dict[str, Any]:
        """Get weather from OpenWeatherMap."""
        url = f"https://api.openweathermap.org/data/2.5/weather"
        params = {"q": location, "appid": self.api_key, "units": "metric"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    return await self._wttr_in(location)
                data = await resp.json()
                return {
                    "location": data.get("name", location),
                    "description": data["weather"][0]["description"],
                    "temperature": round(data["main"]["temp"]),
                    "humidity": data["main"]["humidity"],
                    "wind_speed": data["wind"]["speed"],
                    "icon": data["weather"][0]["icon"],
                }

    async def _wttr_in(self, location: str) -> dict[str, Any]:
        """Fallback: wttr.in (completely free, no key)."""
        url = f"https://wttr.in/{location}?format=j1"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return self._fixture_weather(location)
                data = await resp.json()
                current = data.get("current_condition", [{}])[0]
                return {
                    "location": location,
                    "description": current.get("weatherDesc", [{}])[0].get(
                        "value", "Unknown"
                    ),
                    "temperature": int(current.get("temp_C", 0)),
                    "humidity": int(current.get("humidity", 0)),
                    "wind_speed": int(current.get("windspeedKmph", 0)),
                    "icon": self._wttr_to_icon(current.get("weatherCode", 0)),
                }

    def _wttr_to_icon(self, code: int) -> str:
        """Convert wttr.in weather code to icon."""
        mapping = {
            113: "01d",
            116: "02d",
            119: "03d",
            122: "04d",
            176: "10d",
            179: "13d",
            182: "13d",
            185: "13d",
            200: "11d",
            227: "13d",
            230: "13d",
            248: "50d",
            260: "50d",
            263: "10d",
            266: "10d",
            281: "09d",
            284: "09d",
            293: "10d",
            296: "10d",
            299: "10d",
            302: "10d",
            305: "10d",
            308: "10d",
            311: "09d",
            314: "09d",
            317: "09d",
            320: "13d",
            323: "13d",
            326: "13d",
            329: "13d",
            332: "13d",
            335: "13d",
            338: "13d",
            350: "09d",
            353: "10d",
            356: "10d",
            359: "10d",
            362: "10d",
            365: "09d",
            368: "10d",
            371: "13d",
            377: "09d",
            389: "11d",
            392: "13d",
            395: "13d",
        }
        return mapping.get(code, "01d")
