"""
agents/gemini_client.py — Vertex AI SDK integration for NEXUS

Migration from Google AI Studio (API-key auth) → Vertex AI (IAM/ADC auth).

Auth strategy
─────────────
  On Cloud Run  → Workload Identity / attached Service Account.
                  No key needed. Set PROJECT_ID and VERTEX_LOCATION.
  Local dev     → Application Default Credentials:
                  `gcloud auth application-default login`
  Fallback      → GOOGLE_API_KEY still accepted for dev convenience
                  (we fall through to the REST endpoint in that case).

Environment variables
─────────────────────
  PROJECT_ID       — GCP project (required for Vertex calls)
  VERTEX_LOCATION  — Vertex AI region, e.g. us-central1 (default)
  GOOGLE_API_KEY   — Optional fallback for local dev without ADC
  DEMO_MODE        — 'true' → return fixture data, skip all LLM calls
"""
from __future__ import annotations

import json
import logging
import os
from typing import List, Dict, Optional

logger = logging.getLogger("nexus")

from nexus.config import get_demo_mode as _demo_mode, get_api_key as _api_key


# ---------------------------------------------------------------------------
# Lazy Vertex AI SDK initialisation
# We only import vertexai when actually needed to keep cold-start fast.
# ---------------------------------------------------------------------------

def _get_project() -> str:
    return os.environ.get("PROJECT_ID", os.environ.get("GOOGLE_CLOUD_PROJECT", ""))


def _get_location() -> str:
    return os.environ.get("VERTEX_LOCATION", "us-central1")


def _vertex_available() -> bool:
    """True when Vertex AI SDK is installed and project is configured."""
    try:
        import vertexai  # noqa: F401
        return bool(_get_project())
    except ImportError:
        return False


def _init_vertex() -> None:
    """Idempotent Vertex AI initialisation (ADC / Workload Identity)."""
    import vertexai
    vertexai.init(project=_get_project(), location=_get_location())


# ---------------------------------------------------------------------------
# Session pool for AI Studio fallback (kept for local dev without ADC)
# ---------------------------------------------------------------------------
import aiohttp
_SESSION_POOL: Optional[aiohttp.ClientSession] = None


async def _get_session() -> aiohttp.ClientSession:
    global _SESSION_POOL
    if _SESSION_POOL is None or _SESSION_POOL.closed:
        _SESSION_POOL = aiohttp.ClientSession()
    return _SESSION_POOL


async def close_session() -> None:
    global _SESSION_POOL
    if _SESSION_POOL and not _SESSION_POOL.closed:
        await _SESSION_POOL.close()


# ---------------------------------------------------------------------------
# Internal helpers — Vertex AI path
# ---------------------------------------------------------------------------

def _generate_vertex_sync(
    prompt: str,
    *,
    system_instruction: str = "",
    temperature: float = 0.7,
    max_output_tokens: int = 1024,
    response_mime_type: str = "text/plain",
) -> str:
    """
    Synchronous Vertex AI generation call.
    Runs on the calling thread; callers wrap with asyncio.to_thread.
    """
    from vertexai.generative_models import GenerativeModel, GenerationConfig

    model = GenerativeModel(
        "gemini-2.0-flash-001",
        system_instruction=system_instruction or None,
    )
    cfg = GenerationConfig(
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        response_mime_type=response_mime_type,
    )
    response = model.generate_content(prompt, generation_config=cfg)
    return response.text.strip() if response.text else ""


def _embed_vertex_sync(text: str) -> List[float]:
    """
    Synchronous Vertex AI embedding call.
    Uses text-embedding-004 (768 dims) — same model as before.
    """
    from vertexai.language_models import TextEmbeddingModel

    model = TextEmbeddingModel.from_pretrained("text-embedding-004")
    embeddings = model.get_embeddings([text])
    return embeddings[0].values if embeddings else []


# ---------------------------------------------------------------------------
# Internal helpers — AI Studio REST fallback (uses GOOGLE_API_KEY)
# ---------------------------------------------------------------------------

async def _generate_rest(
    prompt: str,
    *,
    temperature: float = 0.7,
    max_output_tokens: int = 1024,
    response_mime_type: str = "text/plain",
) -> str:
    key = _api_key()
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/"
        f"models/gemini-2.0-flash:generateContent?key={key}"
    )
    payload: dict = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
        },
    }
    if response_mime_type == "application/json":
        payload["generationConfig"]["responseMimeType"] = "application/json"

    try:
        session = await _get_session()
        async with session.post(url, json=payload) as resp:
            if resp.status != 200:
                logger.warning(f"AI Studio REST returned {resp.status}")
                return ""
            data = await resp.json()
            return (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )
    except Exception as exc:
        logger.warning(f"_generate_rest failed: {exc}")
        return ""


async def _embed_rest(text: str) -> List[float]:
    key = _api_key()
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/"
        f"models/text-embedding-004:embedContent?key={key}"
    )
    payload = {
        "model": "models/text-embedding-004",
        "content": {"parts": [{"text": text}]},
    }
    try:
        session = await _get_session()
        async with session.post(url, json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("embedding", {}).get("values", [])
    except Exception as exc:
        logger.warning(f"_embed_rest failed: {exc}")
    return []


# ---------------------------------------------------------------------------
# Demo-mode deterministic stubs
# ---------------------------------------------------------------------------

def _demo_embedding(text: str) -> List[float]:
    import hashlib
    h = hashlib.sha256(text.encode()).digest()
    base = [float(b) / 255.0 for b in h]
    return (base * ((768 // len(base)) + 1))[:768]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def generate_response(prompt: str, context: str = "") -> str:
    if _demo_mode():
        return f"[DEMO] Response to: {prompt[:60]}…"

    full_prompt = f"Context:\n{context}\n\nUser: {prompt}" if context else prompt

    if _vertex_available():
        import asyncio
        _init_vertex()
        return await asyncio.to_thread(
            _generate_vertex_sync, full_prompt,
            system_instruction="You are a helpful multi-agent productivity assistant.",
        )

    return await _generate_rest(full_prompt)


async def generate_plan(
    prompt: str, blackboard_context: str = ""
) -> List[List[Dict[str, str]]]:
    if _demo_mode() or (not _vertex_available() and not _api_key()):
        return [[{"agent": "atlas", "goal": f"Execute: {prompt}"}]]

    system = f"""You are the Lead Architect of the NEXUS multi-agent swarm.
Decompose the user request into sequential execution phases. Each phase is a
list of parallel specialist steps. Each step must have "agent" and "goal".

Available agents: atlas, chrono, sage, mnemo, tasks, briefing, goals, analytics.

{blackboard_context}

Return ONLY a JSON array of phases. Example:
[[{{"agent":"atlas","goal":"Research X"}},{{"agent":"mnemo","goal":"Recall context"}}],
 [{{"agent":"sage","goal":"Structure findings"}}]]
If the task is already done, return [].
"""
    full = f"{system}\n\nUser request: {prompt}"

    try:
        if _vertex_available():
            import asyncio
            _init_vertex()
            raw = await asyncio.to_thread(
                _generate_vertex_sync, full,
                temperature=0.1, max_output_tokens=512,
                response_mime_type="application/json",
            )
        else:
            raw = await _generate_rest(
                full, temperature=0.1, max_output_tokens=512,
                response_mime_type="application/json",
            )

        plan = json.loads(raw)
        return plan if isinstance(plan, list) else [[{"agent": "atlas", "goal": prompt}]]
    except Exception as exc:
        logger.warning(f"generate_plan failed: {exc}")
        return [[{"agent": "atlas", "goal": prompt}]]


async def classify_intent(prompt: str) -> str:
    if _demo_mode() or (not _vertex_available() and not _api_key()):
        p = prompt.lower()
        if any(w in p for w in ["exam", "study", "prep"]):      return "exam_prep"
        if any(w in p for w in ["day", "plan", "schedule"]):    return "day_planner"
        if any(w in p for w in ["research", "find", "search"]): return "research_loop"
        if any(w in p for w in ["task", "todo", "add"]):        return "add_task"
        if any(w in p for w in ["stress", "overwhelmed"]):      return "adaptive"
        return "general"

    intent_prompt = f"""Classify the intent into exactly ONE of:
exam_prep | day_planner | research_loop | add_task | adaptive | general

Prompt: "{prompt}"
Return ONLY the intent name."""

    try:
        if _vertex_available():
            import asyncio
            _init_vertex()
            result = await asyncio.to_thread(
                _generate_vertex_sync, intent_prompt, temperature=0.1, max_output_tokens=20,
            )
        else:
            result = await _generate_rest(intent_prompt, temperature=0.1, max_output_tokens=20)
        return result.strip().lower() or "general"
    except Exception:
        return "general"


async def score_result(goal: str, result: str) -> float:
    if _demo_mode():
        return 1.0

    score_prompt = f"""Score how well this result fulfils the goal.
Goal: {goal}
Result: {result}
Return ONLY a float between 0.0 and 1.0."""

    try:
        if _vertex_available():
            import asyncio
            _init_vertex()
            raw = await asyncio.to_thread(
                _generate_vertex_sync, score_prompt, temperature=0.1, max_output_tokens=10,
            )
        else:
            raw = await _generate_rest(score_prompt, temperature=0.1, max_output_tokens=10)
        return float(raw.strip())
    except Exception:
        return 0.9


async def get_completion(system_prompt: str, user_prompt: str) -> str:
    return await generate_response(user_prompt, context=system_prompt)


async def generate_embedding(text: str) -> List[float]:
    if _demo_mode():
        return _demo_embedding(text)

    if _vertex_available():
        import asyncio
        _init_vertex()
        try:
            result = await asyncio.to_thread(_embed_vertex_sync, text)
            if result:
                return result
        except Exception as exc:
            logger.warning(f"Vertex embedding failed, falling back to REST: {exc}")

    if _api_key():
        result = await _embed_rest(text)
        if result:
            return result

    logger.error("generate_embedding: no available backend — returning empty vector")
    return []
