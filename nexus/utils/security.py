"""
utils/security.py — NEXUS Security (Fixed)

FIX: rate_limit_store note added — deploy behind Redis for multi-worker setups.
FIX: get_client_id returns request.client.host safely (no crash on None).
"""
from __future__ import annotations

import hmac
import time
import logging
from collections import defaultdict

from fastapi import HTTPException, Request, Header

logger = logging.getLogger("nexus")

from nexus.config import get_nexus_api_key, get_rate_limit_requests, get_rate_limit_window

API_KEY = get_nexus_api_key()
RATE_LIMIT_REQUESTS = get_rate_limit_requests()
RATE_LIMIT_WINDOW = get_rate_limit_window()

# NOTE: In-process dict — works for single-worker deployments only.
# For multi-worker / Kubernetes, replace with Redis (e.g. aioredis).
rate_limit_store: dict[str, list[float]] = defaultdict(list)


def verify_api_key(authorization: str = Header(None)) -> str:
    """Verify Bearer token using timing-attack-resistant comparison."""
    if not API_KEY:
        return "demo"  # no key configured → open access (dev mode)

    if not authorization:
        raise HTTPException(401, detail="Authorization header required")

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            401, detail="Invalid format. Use: Authorization: Bearer <api_key>"
        )

    token = authorization[7:]
    if not hmac.compare_digest(token.encode(), API_KEY.encode()):
        raise HTTPException(401, detail="Invalid API key")

    return "authenticated"


def check_rate_limit(identifier: str) -> bool:
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    rate_limit_store[identifier] = [
        t for t in rate_limit_store[identifier] if t > window_start
    ]
    if len(rate_limit_store[identifier]) >= RATE_LIMIT_REQUESTS:
        return False
    rate_limit_store[identifier].append(now)
    return True


def get_client_id(request: Request) -> str:
    """Best-effort client identifier — handles proxies and missing client."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()

    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer ") and API_KEY:
        token = auth_header[7:]
        if hmac.compare_digest(token.encode(), API_KEY.encode()):
            return "authenticated"

    # FIX: request.client can be None in test environments
    return request.client.host if request.client else "unknown"
