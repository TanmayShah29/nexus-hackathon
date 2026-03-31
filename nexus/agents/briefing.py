"""
briefing.py — Briefing Agent (Weather MCP Integration)
"""

from datetime import datetime
import logging

logger = logging.getLogger("nexus")

from nexus.models.schemas import AgentResult, SuggestionChip
from nexus.agents.base import BaseAgent
from nexus.agents.blackboard import Blackboard
from nexus.config import get_demo_mode

_DEMO = get_demo_mode()


class BriefingAgent(BaseAgent):
    """
    Briefing agent - context synthesis and adaptive communication.
    Uses WeatherMCP for real weather data + CryptoMCP for market updates.
    """

    def __init__(self, blackboard: Blackboard):
        super().__init__(name="briefing", blackboard=blackboard)

    async def think(self, prompt: str) -> AgentResult:
        """Execute the briefing logic."""
        prompt_lower = prompt.lower()

        self.trace("Analyzing briefing context")

        if any(w in prompt_lower for w in ["stressed", "overwhelmed", "tired"]):
            return await self._run_adaptive()

        self.trace("Gathering today's context", status="running")

        location = self.get_state("location", "Mumbai")

        weather_data = {}
        crypto_data = {}

        if not _DEMO:
            try:
                from nexus.mcp_servers.weather_mcp import WeatherMCP

                weather_data = await WeatherMCP(demo_mode=False).get_current(location)
            except Exception as e:
                logger.warning(f"Briefing weather MCP failed: {e}")

        if not _DEMO:
            try:
                from nexus.mcp_servers.finance_mcp import FinanceMCP

                btc = await FinanceMCP(demo_mode=False).get_crypto_price("bitcoin")
                sol = await FinanceMCP(demo_mode=False).get_crypto_price("solana")
                crypto_data = {"btc": btc, "sol": sol}
            except Exception as e:
                logger.warning(f"Briefing crypto MCP failed: {e}")

        self.trace(f"Context for {location} synthesis complete", status="done")

        greeting = self._get_greeting()

        temp = weather_data.get("temperature", 28) if weather_data else 28
        desc = (
            weather_data.get("description", "Clear sky")
            if weather_data
            else "Clear sky"
        )

        btc_price = (
            crypto_data.get("btc", {}).get("price", 65000) if crypto_data else 65000
        )
        sol_price = crypto_data.get("sol", {}).get("price", 140) if crypto_data else 140

        markdown = f"""# {greeting}

## Weather in {location}
{desc}, {temp}°C

## Crypto Market
- BTC: ${btc_price:,}
- SOL: ${sol_price}

## Your Focus
The Research agent is ready for deep-dives, and the Scheduler has your calendar under control. What's our first move?
"""

        return self.create_result(
            summary=f"Morning brief: {desc}, {temp}°C in {location}",
            markdown=markdown,
            suggestions=[
                SuggestionChip(
                    label="Check my tasks",
                    prompt="What's on my list today?",
                    agent_hint="tasks",
                ),
                SuggestionChip(
                    label="Start research",
                    prompt="I need to learn something new",
                    agent_hint="atlas",
                ),
            ],
        )

    async def _run_adaptive(self) -> AgentResult:
        markdown = "# I hear you.\n\nIt's okay to feel overwhelmed. I've signaled the swarm to simplify your day.\n\n### Here's the plan:\n1. **Focus on one thing.**\n2. **I've deferred non-urgent tasks.**\n3. **Take a 5-minute breather.**\n\nHow can I make the next hour easier for you?"
        return self.create_result(
            summary="Adaptive mode activated: prioritizing well-being.",
            markdown=markdown,
            workflow_type="adaptive",
        )

    def _get_greeting(self) -> str:
        hour = datetime.now().hour
        if hour < 12:
            return "Good Morning"
        elif hour < 17:
            return "Good Afternoon"
        else:
            return "Good Evening"
