# NEXUS — Judges' Demo Guide

Open **Mission Control** at `http://localhost:8000/studio` and try the prompts below. Watch the D3 swarm graph — agent nodes light up and pulse as each specialist fires.

---

## Scenario 1 — Research & Structure (2-phase swarm)

> *"Research the benefits of deep work and structure it into a study plan."*

**What happens:**
- Phase 1 (parallel): **Atlas** searches Tavily + Wikipedia → writes findings to Blackboard. **Mnemo** recalls any prior context from the vector vault.
- Phase 2 (parallel): **Sage** reads Atlas's Blackboard state → creates a structured Notion-ready document. **Chrono** schedules deep-work blocks based on the findings.

---

## Scenario 2 — Daily Briefing (context synthesis)

> *"Give me my morning briefing."*

**What happens:**
- **Briefing** fetches weather (OpenWeatherMap → wttr.in fallback), reads location from Blackboard, synthesises a daily context card.
- Suggestion chips appear to chain into Tasks and Chrono.

---

## Scenario 3 — Task & Goal Decomposition

> *"I want to learn machine learning in 90 days. Create a plan and add the first week's tasks."*

**What happens:**
- Phase 1: **Goals** decomposes into 30/60/90-day milestones.
- Phase 2: **Tasks** reads the Goals Blackboard state → creates week-1 tasks. **Chrono** schedules time blocks.
- All results written to shared Blackboard and synced to Supabase L3.

---

## Scenario 4 — Memory Persistence Test

> *"Remember that I prefer morning deep work sessions and short evening reviews."*

**What happens:**
- **Mnemo** detects the "remember" keyword → generates a Gemini embedding → writes to Supabase L4 pgvector vault.
- Subsequent prompts will recall this preference via cosine similarity search.
- Check `http://localhost:8000/memory` to see the live trace stream and memory count increment.

---

## Scenario 5 — Local Booster (zero-latency)

> *"What is 2456 * 789?"*  
> *"What time is it?"*

**What happens:**
- The **NEXUS Booster** intercepts before any LLM call.
- Math is evaluated by the recursive-descent parser in `logic/booster.py`.
- Time is resolved from the server clock with timezone.
- Response arrives in &lt;5ms. No Gemini call. No agent activation.

---

## What to look for in the UI

| Signal | Meaning |
|--------|---------|
| Node brightens + inner ring pulses | Agent is `running` |
| Pulse ball travels along edge | Signal flowing orchestrator → agent |
| Return pulse (agent → nexus) | Agent reported `done` |
| Node dims back to 22% opacity | Agent complete, awaiting next prompt |
| Suggestion chips appear | Agent returned follow-up prompts |
| Memory Vault counter increments | Mnemo wrote to Supabase L4 |

---

## API endpoints for judges

```
GET  /health              → system status, mode, agent count
GET  /agents              → all specialist identities
POST /chat                → SSE swarm execution stream
POST /plan                → generate phase plan (no execution)
GET  /memory/default_user → all 4 memory layers
GET  /memory-search?query= → semantic vector search
GET  /docs                → Swagger UI
```
