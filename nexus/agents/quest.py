"""quest.py — Quest Goals Agent"""

import os
from typing import Any

DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"


class QuestAgent:
    """Quest: Goals agent - goal strategist."""

    def __init__(self, demo_mode: bool = DEMO_MODE):
        self.demo_mode = demo_mode

    async def run(self, prompt: str) -> dict[str, Any]:
        return {"status": "stub", "prompt": prompt}
