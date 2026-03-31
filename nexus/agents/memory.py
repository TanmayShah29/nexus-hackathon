import asyncio
import os
from typing import Any, Dict, List
import logging

logger = logging.getLogger("nexus")

from nexus.models.schemas import AgentResult, SuggestionChip
from nexus.agents.base import BaseAgent
from nexus.agents.blackboard import Blackboard
from nexus.memory.vector_store import VectorStore


class MnemoAgent(BaseAgent):
    """
    NEXUS Memory Specialist (Mnemo)
    Decision 92: Characterful identity and semantic retrieval.
    Specializes in the 4-layer persistence hierarchy:
    L1: Reactive state (Blackboard)
    L2: Session persistence (JSON)
    L3: Contextual memory (Recent facts)
    L4: Semantic vault (Vector Search)
    """

    def __init__(self, blackboard: Blackboard):
        super().__init__(name="mnemo", blackboard=blackboard)
        self.vector_store = VectorStore(demo_mode=False)
        self.context_key = "memory.context"

    async def think(self, prompt: str) -> AgentResult:
        """
        Decision 2: Specialist Reasoning.
        Semantic search + Contextual synthesis across Supabase levels.
        """
        from nexus.memory.supabase_client import get_supabase_client

        sb = get_supabase_client()

        self.trace("Analyzing intent for memory retrieval...")

        # 1. LAYER 4: SEMANTIC SEARCH
        self.trace(
            f"Searching Layer 4 Semantic Vault: '{prompt[:30]}...'", status="running"
        )
        results = await self.vector_store.search(prompt, top_k=3)

        # 2. LAYER 3: CONTEXTUAL LOOKUP
        # Check Supabase first, fallback to Blackboard
        self.trace("Syncing with Layer 3 Blackboard Facts", status="running")
        sb_context = sb.get_context(self.context_key) if sb.is_active() else None
        context = sb_context or self.get_state(self.context_key) or []

        # 3. SYNTHESIS
        self.trace("Synthesizing unified briefing", status="running")
        await asyncio.sleep(0.5)

        # 4. MEMORY PERSISTENCE
        # If the prompt looks like a fact or preference, save it!
        if len(prompt) > 20 and any(
            kw in prompt.lower() for kw in ["remember", "prefer", "i like", "bias"]
        ):
            await self.vector_store.add_document(
                doc_id=f"mem_{os.urandom(4).hex()}",
                content=prompt,
                metadata={"type": "preference", "source": "prompt", "agent": "mnemo"},
                thread_id=self.session_id,
            )
            self.trace("Persistent memory indexed to Layer 4 (Supabase)", status="done")

            # Update Layer 3: Persistence context fact
            context.append(f"Preference noted: {prompt[:40]}...")
            if sb.is_active():
                sb.update_context(self.context_key, context)
            self.set_state(self.context_key, context)

        # 5. REPORT GENERATION
        summary = f"Recalled {len(results)} semantic nodes and synced {len(context)} facts from Supabase Context."

        markdown = f"""
# Mnemo Recall: Cognitive Context

### 🧠 Semantic Vault (Layer 4)
{self._format_results(results)}

### 📍 Contextual Facts (Layer 3)
{self._format_context(context)}

---
*Mnemo (Memory & Persistence Specialist)*
        """

        suggestions = [
            SuggestionChip(
                label="Audit Memory Graph",
                prompt="Mnemo, show me all recent memory writes",
            ),
            SuggestionChip(
                label="Wipe Session Context",
                prompt="Mnemo, clear Layer 3 cache for this thread",
            ),
        ]

        # Update Blackboard
        self.set_state("memory.context_injected", True)
        self.set_state("memory.last_recall", [r["doc_id"] for r in results])

        self.trace("Recall operation complete", status="done")

        return self.create_result(
            summary=summary,
            markdown=markdown,
            suggestions=suggestions,
            confidence=0.98 if results else 0.85,
        )

    def _format_results(self, results: List[Dict]) -> str:
        if not results:
            return "*No semantic overlaps found in the current vault.*"
        items = []
        for r in results:
            content_snippet = r["content"][:80] + "..."
            items.append(
                f"- **{r['doc_id']}**: {content_snippet} (Score: {r['score']})"
            )
        return "\n".join(items)

    def _format_context(self, context: List[Any]) -> str:
        if not context:
            return "*Layer 3 Context is currently empty.*"
        return "\n".join([f"- {item}" for item in context])
