"""
gmail_mcp.py — Gmail MCP (fixture)
"""

import os
from typing import Any


DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"


GMAIL_FIXTURE = [
    {
        "id": "1",
        "subject": "Welcome to NEXUS",
        "from": "team@nexus.ai",
        "date": "2025-03-27",
        "snippet": "Welcome to NEXUS!",
    },
    {
        "id": "2",
        "subject": "Interview Confirmation",
        "from": "hr@company.com",
        "date": "2025-03-26",
        "snippet": "Your interview is confirmed for tomorrow.",
    },
    {
        "id": "3",
        "subject": "Code Review Request",
        "from": "dev@company.com",
        "date": "2025-03-25",
        "snippet": "Can you review my PR?",
    },
]


class GmailMCP:
    """
    Gmail integration with fixture fallback.
    """

    def __init__(self, demo_mode: bool = DEMO_MODE):
        self.demo_mode = demo_mode or DEMO_MODE

    async def get_inbox(self, max_results: int = 10) -> list[dict[str, Any]]:
        """Get recent emails."""
        if self.demo_mode:
            return GMAIL_FIXTURE[:max_results]

        raise NotImplementedError("Real Gmail API not implemented")

    async def send_email(self, to: str, subject: str, body: str) -> dict[str, Any]:
        """Send an email."""
        if self.demo_mode:
            return {"id": "sent_1", "to": to, "subject": subject, "status": "sent"}

        raise NotImplementedError("Real Gmail API not implemented")
