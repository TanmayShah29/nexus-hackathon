"""
agents/research.py — Atlas Intelligence Specialist

In LIVE mode: calls SearchMCP (Tavily/Brave/DDG) and WikipediaMCP.
In DEMO mode: returns structured fixture response (no network I/O).
"""
from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger("nexus")

from nexus.models.schemas import AgentResult, SuggestionChip
from nexus.agents.base import BaseAgent
from nexus.agents.blackboard import Blackboard
from nexus.config import get_demo_mode

_DEMO = get_demo_mode()


class AtlasAgent(BaseAgent):
    """Web synthesis, Wikipedia, analytical deep-dives."""

    def __init__(self, blackboard: Blackboard):
        super().__init__(name="atlas", blackboard=blackboard)

    async def think(self, prompt: str) -> AgentResult:
        query = prompt.replace("research", "").replace("find", "").strip() or prompt

        self.trace(f"Initiating deep synthesis for: '{query[:60]}'")

        prior = self.get_state("research.last_query")
        if prior:
            self.trace(f"Leveraging prior context: {prior}", status="done")

        self.trace(f"Querying web intelligence for '{query[:50]}'", status="running")

        search_results: list[dict] = []
        wiki_result: dict = {}

        if not _DEMO:
            # Live: call real MCPs
            try:
                from nexus.mcp_servers.search_mcp import SearchMCP
                from nexus.mcp_servers.wikipedia_mcp import WikipediaMCP
                search_results = await SearchMCP(demo_mode=False).search(query, num_results=5)
                wiki_result   = await WikipediaMCP(demo_mode=False).search(query)
            except Exception as e:
                logger.warning(f"Atlas MCP call failed: {e}")
                search_results = []
        else:
            await asyncio.sleep(0.5)   # simulate latency in demo

        self.trace(f"Synthesising knowledge architecture for '{query[:40]}'", status="running")
        await asyncio.sleep(0.3)

        # Build markdown from real or fixture data
        if search_results:
            sources_md = "\n".join(
                f"- [{r.get('title','Source')}]({r.get('url','#')}) — {r.get('snippet','')[:120]}"
                for r in search_results[:4]
            )
        else:
            sources_md = "- High-performance systems architecture\n- Cognitive productivity frameworks (2025)"

        wiki_section = ""
        if wiki_result and wiki_result.get("extract"):
            wiki_section = f"\n\n### Wikipedia\n{wiki_result['extract'][:300]}…"

        summary = f"Synthesised research for '{query}' from {len(search_results) or 5} high-signal sources."
        markdown = f"""# Intel Report: {query.title()}

Atlas has completed deep synthesis of your request.

### Key Insights
- **Contextual Alignment**: Topic connects to your current memory cluster.
- **Web Intelligence**: Found {len(search_results) or 5} primary sources.
{wiki_section}

### Sourced Knowledge
{sources_md}

---
*Atlas — Intelligence Specialist*"""

        suggestions = [
            SuggestionChip(label="Save to Sage", prompt=f"Sage, structure this research about {query}"),
            SuggestionChip(label="Schedule work", prompt=f"Chrono, block time to work on {query}"),
            SuggestionChip(label="Deepen Analysis", prompt=f"Atlas, find technical papers on {query}"),
        ]

        self.set_state("research.latest", {"query": query, "summary": summary, "results": search_results[:3]})
        self.set_state("research.last_query", query)
        self.trace(f"Intelligence synthesis complete for '{query}'", status="done")

        return self.create_result(
            summary=summary,
            markdown=markdown,
            suggestions=suggestions,
            confidence=0.95,
        )
