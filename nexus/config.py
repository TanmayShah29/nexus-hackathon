"""
config.py — NEXUS Centralized Configuration

Single source of truth for all environment variables and settings.
All modules must import from here — never call os.getenv() directly elsewhere.

IMPORTANT: lru_cache caches the value at first call. If you need to test
with different env values, clear the cache: config_fn.cache_clear()
"""
from __future__ import annotations

import os
from functools import lru_cache

VERSION = "1.0.0"


@lru_cache()
def get_demo_mode() -> bool:
    return os.getenv("DEMO_MODE", "true").lower() == "true"


@lru_cache()
def get_api_key() -> str:
    return os.getenv("GOOGLE_API_KEY", "")


@lru_cache()
def get_nexus_api_key() -> str:
    return os.getenv("NEXUS_API_KEY", "")


@lru_cache()
def get_port() -> int:
    return int(os.getenv("PORT", "8000"))


@lru_cache()
def get_max_prompt_length() -> int:
    return int(os.getenv("MAX_PROMPT_LENGTH", "10000"))


@lru_cache()
def get_rate_limit_requests() -> int:
    return int(os.getenv("RATE_LIMIT_REQUESTS", "20"))


@lru_cache()
def get_rate_limit_window() -> int:
    return int(os.getenv("RATE_LIMIT_WINDOW", "60"))


@lru_cache()
def get_allowed_origins() -> str:
    return os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5500,http://localhost:8000,http://127.0.0.1:5500",
    )


@lru_cache()
def get_supabase_url() -> str:
    return os.getenv("SUPABASE_URL", "")


@lru_cache()
def get_supabase_anon_key() -> str:
    return os.getenv("SUPABASE_ANON_KEY", "")


@lru_cache()
def get_supabase_service_role_key() -> str:
    return os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")


@lru_cache()
def get_tavily_api_key() -> str:
    return os.getenv("TAVILY_API_KEY", "")


@lru_cache()
def get_brave_api_key() -> str:
    return os.getenv("BRAVE_API_KEY", "")


@lru_cache()
def get_notion_token() -> str:
    # Support both NOTION_TOKEN and legacy NOTION_API_KEY
    return os.getenv("NOTION_TOKEN", os.getenv("NOTION_API_KEY", ""))


@lru_cache()
def get_openweather_api_key() -> str:
    return os.getenv("OPENWEATHER_API_KEY", "")


@lru_cache()
def get_gmail_api_key() -> str:
    return os.getenv("GMAIL_API_KEY", "")


@lru_cache()
def get_firebase_project_id() -> str:
    return os.getenv("FIREBASE_PROJECT_ID", "")
