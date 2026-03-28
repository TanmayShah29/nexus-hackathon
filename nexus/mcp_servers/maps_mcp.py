"""
maps_mcp.py — Maps MCP (Google Maps or fixture)
"""

import os
from typing import Any


DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"


MAPS_FIXTURE = {
    "directions": [
        {
            "start": "Home",
            "end": "Office",
            "distance": "5.2 km",
            "duration": "18 min",
            "route": ["Main St", "Highway 101", "Tech Blvd"],
        }
    ],
    "places": [
        {
            "name": "Coffee Shop",
            "address": "123 Main St",
            "rating": 4.5,
            "distance": "0.3 km",
        },
        {
            "name": "Library",
            "address": "456 Oak Ave",
            "rating": 4.8,
            "distance": "1.2 km",
        },
    ],
}


class MapsMCP:
    """
    Google Maps integration with fixture fallback.
    """

    def __init__(self, demo_mode: bool = DEMO_MODE):
        self.demo_mode = demo_mode or DEMO_MODE

    async def get_directions(
        self, origin: str, destination: str
    ) -> list[dict[str, Any]]:
        """Get directions between two locations."""
        if self.demo_mode:
            return MAPS_FIXTURE["directions"]

        raise NotImplementedError("Real Google Maps not implemented")

    async def find_nearby(
        self, location: str, query: str, radius: int = 1000
    ) -> list[dict[str, Any]]:
        """Find nearby places."""
        if self.demo_mode:
            return MAPS_FIXTURE["places"]

        raise NotImplementedError("Real Google Maps not implemented")
