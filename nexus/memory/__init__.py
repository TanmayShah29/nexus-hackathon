"""
memory/__init__.py

Re-exports the canonical database client under both names so that:
  - New code:  from nexus.memory.alloydb_client import get_db_client
  - Legacy:    from nexus.memory.supabase_client import get_supabase_client
both work without any changes in agents, routes, or observability.
"""
from nexus.memory.alloydb_client import (   # noqa: F401
    AlloyDBClient,
    get_db_client,
    get_supabase_client,   # backwards-compat alias
)
