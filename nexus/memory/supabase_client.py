"""
memory/supabase_client.py — Backwards-compatibility shim.

This module previously contained the Supabase-based persistence client.
The implementation has been migrated to alloydb_client.py (AlloyDB AI /
psycopg2 + pgvector).

All existing `from nexus.memory.supabase_client import get_supabase_client`
calls continue to work unchanged — they now resolve to the AlloyDB client.
"""
from nexus.memory.alloydb_client import (  # noqa: F401
    AlloyDBClient as SupabaseMemoryClient,   # type alias for old code
    get_db_client,
    get_supabase_client,
)

__all__ = ["SupabaseMemoryClient", "get_db_client", "get_supabase_client"]
