"""
config.py — NEXUS Centralised Configuration

Single source of truth for ALL environment variables.
Never call os.getenv() elsewhere in the codebase.

lru_cache note: values are frozen at first call. In tests, call
<fn>.cache_clear() before changing env vars.
"""
from __future__ import annotations

import os
from functools import lru_cache

VERSION = "1.0.0"

# ── Core ──────────────────────────────────────────────────────

@lru_cache()
def get_demo_mode() -> bool:
    return os.getenv("DEMO_MODE", "true").lower() == "true"

@lru_cache()
def get_port() -> int:
    # Cloud Run injects PORT=8080; local default 8000.
    return int(os.getenv("PORT", "8080"))

@lru_cache()
def get_nexus_api_key() -> str:
    return os.getenv("NEXUS_API_KEY", "")

@lru_cache()
def get_allowed_origins() -> str:
    return os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5500,http://localhost:8000,http://127.0.0.1:5500",
    )

@lru_cache()
def get_max_prompt_length() -> int:
    return int(os.getenv("MAX_PROMPT_LENGTH", "10000"))

@lru_cache()
def get_rate_limit_requests() -> int:
    return int(os.getenv("RATE_LIMIT_REQUESTS", "20"))

@lru_cache()
def get_rate_limit_window() -> int:
    return int(os.getenv("RATE_LIMIT_WINDOW", "60"))

# ── GCP / Vertex AI ──────────────────────────────────────────

@lru_cache()
def get_gcp_project() -> str:
    return os.getenv("PROJECT_ID", os.getenv("GOOGLE_CLOUD_PROJECT", ""))

@lru_cache()
def get_vertex_location() -> str:
    return os.getenv("VERTEX_LOCATION", "us-central1")

# Fallback key for local dev without ADC (never set in Cloud Run)
@lru_cache()
def get_api_key() -> str:
    return os.getenv("GOOGLE_API_KEY", "")

# ── AlloyDB ──────────────────────────────────────────────────

@lru_cache()
def get_db_host() -> str:
    return os.getenv("DB_HOST", "")

@lru_cache()
def get_db_port() -> int:
    return int(os.getenv("DB_PORT", "5432"))

@lru_cache()
def get_db_name() -> str:
    return os.getenv("DB_NAME", "nexus")

@lru_cache()
def get_db_user() -> str:
    return os.getenv("DB_USER", "")

@lru_cache()
def get_db_pass() -> str:
    return os.getenv("DB_PASS", "")

@lru_cache()
def get_db_pool_min() -> int:
    return int(os.getenv("DB_POOL_MIN", "2"))

@lru_cache()
def get_db_pool_max() -> int:
    return int(os.getenv("DB_POOL_MAX", "10"))

# ── Search MCPs ───────────────────────────────────────────────

@lru_cache()
def get_tavily_api_key() -> str:
    return os.getenv("TAVILY_API_KEY", "")

@lru_cache()
def get_brave_api_key() -> str:
    return os.getenv("BRAVE_API_KEY", "")

# ── External integrations ────────────────────────────────────

@lru_cache()
def get_notion_token() -> str:
    return os.getenv("NOTION_TOKEN", os.getenv("NOTION_API_KEY", ""))

@lru_cache()
def get_openweather_api_key() -> str:
    return os.getenv("OPENWEATHER_API_KEY", "")

@lru_cache()
def get_gmail_api_key() -> str:
    return os.getenv("GMAIL_API_KEY", "")

# ── Legacy aliases (kept so nothing else breaks) ─────────────
# These previously pointed at Supabase. They now return "" which
# causes the AlloyDB client to be used instead.

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
def get_firebase_project_id() -> str:
    return os.getenv("FIREBASE_PROJECT_ID", "")
