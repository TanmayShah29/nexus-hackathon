"""
gemini_client.py — Gemini API integration for NEXUS with reasoning and reflection.
"""

import json
import logging
import aiohttp
from typing import Optional, List, Dict

logger = logging.getLogger("nexus")

from nexus.config import get_demo_mode as _demo_mode, get_api_key as _api_key

GEMINI_API_KEY = _api_key()


# Global session pool
_SESSION_POOL: Optional[aiohttp.ClientSession] = None


async def get_session() -> aiohttp.ClientSession:
    """Get or create a global ClientSession."""
    global _SESSION_POOL
    if _SESSION_POOL is None or _SESSION_POOL.closed:
        _SESSION_POOL = aiohttp.ClientSession()
    return _SESSION_POOL


async def close_session():
    """Close the global session pool."""
    global _SESSION_POOL
    if _SESSION_POOL and not _SESSION_POOL.closed:
        await _SESSION_POOL.close()


async def classify_intent(prompt: str) -> str:
    """
    Classify the user's intent into a workflow type.
    Used for demo routing and fallback logic.
    """
    if not _api_key() or _demo_mode():
        prompt_lower = prompt.lower()
        if any(w in prompt_lower for w in ["exam", "study", "prep"]):
            return "exam_prep"
        if any(w in prompt_lower for w in ["day", "plan", "schedule"]):
            return "day_planner"
        if any(w in prompt_lower for w in ["research", "find", "search"]):
            return "research_loop"
        if any(w in prompt_lower for w in ["task", "todo", "add"]):
            return "add_task"
        if any(w in prompt_lower for w in ["stress", "overwhelmed", "tired"]):
            return "adaptive"
        return "general"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={_api_key()}"

    prompt_text = f"""Classify the user's intent into exactly ONE of the following types:
- exam_prep: Preparing for exams, tests, or learning new subjects.
- day_planner: Planning daily schedule, meetings, and tasks.
- research_loop: Deep research on a specific topic.
- add_task: Adding a simple task or todo item.
- adaptive: User is feeling stressed or overwhelmed.
- general: Any other general query.

User prompt: "{prompt}"
Return ONLY the intent name."""

    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 20},
    }

    try:
        session = await get_session()
        async with session.post(url, json=payload) as response:
            if response.status != 200:
                return "general"
            data = await response.json()
            text = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "general")
            )
            return text.strip().lower()
    except Exception as e:
        logger.warning(f"classify_intent failed: {e}")
        return "general"


async def generate_plan(
    prompt: str, blackboard_context: str = ""
) -> List[List[Dict[str, str]]]:
    """
    Use Gemini to generate a dynamic execution plan.
    Blackboard context allows for re-planning mid-workflow.
    Now grouped into phases for parallel execution.
    """
    if not _api_key() or _demo_mode():
        return [[{"agent": "research", "goal": f"Execute: {prompt}"}]]

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={_api_key()}"

    system_prompt = f"""You are the Lead Architect of the NEXUS multi-agent swarm.
Your job is to take a user request and decompose it into a sequence of execution phases. Each phase can contain multiple specialist agent calls that can run in parallel.

Available Agents:
- atlas: Web search, intelligence synthesis, and analytical pattern detection.
- chrono: Calendar management, priority task control, and commitment tracking.
- sage: Knowledge structuring, strategic roadmapping, and permanent storage.
- mnemo: Context recall, semantic briefing, and user preference synthesis.
- tasks: Individual task management, todo updates, and execution steps.
- briefing: Daily context synthesis and morning briefings.
- goals: 90-day roadmaps and OKR decomposition.
- tools: Direct utility access for currency conversion, crypto/stock prices, country data, news, and dictionary definitions.

{blackboard_context}

Output format: Return ONLY a JSON list of phases. Each phase is a list of steps. Each step must have "agent" and "goal".
Example: [[{{"agent": "atlas", "goal": "Find X"}}, {{"agent": "chrono", "goal": "Check schedule"}}], [{{"agent": "sage", "goal": "Save X"}}]]
If the context shows the work is already done, return an empty list [].
"""

    payload = {
        "contents": [
            {"parts": [{"text": f"{system_prompt}\n\nUser request: {prompt}"}]}
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 500,
            "responseMimeType": "application/json",
        },
    }

    try:
        session = await get_session()
        async with session.post(url, json=payload) as response:
            if response.status != 200:
                return [[{"agent": "research", "goal": prompt}]]
            data = await response.json()
            text = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "[]")
            )
            plan = json.loads(text)
            return (
                plan
                if isinstance(plan, list)
                else [[{"agent": "research", "goal": prompt}]]
            )
    except Exception as e:
        print(f"Plan generation failed: {e}")
        return [[{"agent": "research", "goal": prompt}]]


async def score_result(goal: str, result: str) -> float:
    """
    Gemini scores an agent's output from 0.0 to 1.0.
    """
    if not _api_key() or _demo_mode():
        return 1.0

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={_api_key()}"

    prompt = f"""Score the following AI Agent result based on how well it fulfilled the GOAL.
Goal: {goal}
Result: {result}

Return ONLY a number between 0.0 and 1.0. 
1.0 means perfect, 0.0 means complete failure or irrelevant."""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 10},
    }

    try:
        session = await get_session()
        async with session.post(url, json=payload) as response:
            if response.status != 200:
                return 0.9
            data = await response.json()
            text = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "0.9")
            )
            return float(text.strip())
    except Exception as e:
        logger.warning(f"score_result failed: {e}")
        return 0.9


async def generate_response(prompt: str, context: str = "") -> str:
    """Standard response generator."""
    if not _api_key() or _demo_mode():
        return f"AI Response to: {prompt[:50]}..."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={_api_key()}"

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": f"You are a helpful AI assistant. Context:\n{context}\n\nUser: {prompt}"
                    }
                ]
            }
        ],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1000},
    }

    try:
        session = await get_session()
        async with session.post(url, json=payload) as response:
            if response.status != 200:
                return "Error generating response."
            data = await response.json()
            return (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )
    except Exception as e:
        logger.warning(f"generate_response failed: {e}")
        return "Error in LLM call."


async def get_completion(system_prompt: str, user_prompt: str) -> str:
    """
    Direct completion helper for single-shot tasks (routing, summaries).
    """
    return await generate_response(user_prompt, context=system_prompt)


async def generate_embedding(text: str) -> List[float]:
    """
    Generate vector embeddings using Gemini API.
    """
    if not _api_key() or _demo_mode():
        # Pseudo-random but deterministic for mock mode — 768-dim to match real embedding dimensions
        import hashlib

        h = hashlib.sha256(text.encode()).digest()  # 32 bytes
        base = [float(b) / 255.0 for b in h]
        # Tile up to 768 dimensions
        repeated = (base * ((768 // len(base)) + 1))[:768]
        return repeated

    url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={_api_key()}"
    payload = {
        "model": "models/text-embedding-004",
        "content": {"parts": [{"text": text}]},
    }

    try:
        session = await get_session()
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("embedding", {}).get("values", [])
            else:
                logger.warning(
                    f"Embedding failed with status {response.status}: {await response.text()}"
                )
    except Exception as e:
        logger.warning(f"generate_embedding error: {e}")

    return []
