"""
calendar_mcp.py — Calendar MCP (Google Calendar or fixture)
"""

import os
from datetime import datetime, timedelta
from typing import Any


DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"


CALENDAR_FIXTURE = [
    {
        "id": "1",
        "title": "Team Standup",
        "start": "2025-03-27T09:00:00",
        "end": "2025-03-27T09:30:00",
        "location": "Zoom",
    },
    {
        "id": "2",
        "title": "Python Interview Prep",
        "start": "2025-03-27T14:00:00",
        "end": "2025-03-27T15:00:00",
        "location": "Home",
    },
    {
        "id": "3",
        "title": "Code Review",
        "start": "2025-03-27T11:00:00",
        "end": "2025-03-27T11:30:00",
        "location": "Office",
    },
]


class CalendarMCP:
    """
    Google Calendar integration with fixture fallback.
    """

    def __init__(self, demo_mode: bool = DEMO_MODE):
        self.demo_mode = demo_mode or DEMO_MODE

    async def get_events(self, days: int = 7) -> list[dict[str, Any]]:
        """Get calendar events for the next N days."""
        if self.demo_mode:
            return CALENDAR_FIXTURE

        raise NotImplementedError("Real Google Calendar not implemented")

    async def create_event(
        self, title: str, start: str, end: str, location: str = ""
    ) -> dict[str, Any]:
        """Create a new calendar event."""
        if self.demo_mode:
            event = {
                "id": str(len(CALENDAR_FIXTURE) + 1),
                "title": title,
                "start": start,
                "end": end,
                "location": location,
            }
            CALENDAR_FIXTURE.append(event)
            return event

        raise NotImplementedError("Real Google Calendar not implemented")

    async def find_free_slots(
        self, date: str, duration_minutes: int = 60
    ) -> list[dict[str, str]]:
        """Find free time slots on a given date."""
        if self.demo_mode:
            return [
                {"start": f"{date}T16:00:00", "end": f"{date}T17:00:00"},
                {"start": f"{date}T17:00:00", "end": f"{date}T18:00:00"},
            ]

        raise NotImplementedError("Real Google Calendar not implemented")
