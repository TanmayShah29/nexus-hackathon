"""
filesystem_mcp.py — Filesystem MCP (local file read/write)
"""

import os
from pathlib import Path
from typing import Any


DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"


class FilesystemMCP:
    """
    Local filesystem operations.
    """

    def __init__(self, base_dir: str = "/tmp/nexus_files"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def read_file(self, filename: str) -> dict[str, Any]:
        """Read a file."""
        filepath = self.base_dir / filename
        if not filepath.exists():
            return {"error": "File not found", "filename": filename}

        content = filepath.read_text()
        return {"filename": filename, "content": content}

    async def write_file(self, filename: str, content: str) -> dict[str, Any]:
        """Write content to a file."""
        filepath = self.base_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content)
        return {"filename": filename, "status": "written"}

    async def list_files(self, pattern: str = "*") -> list[str]:
        """List files matching pattern."""
        return [str(p.name) for p in self.base_dir.glob(pattern)]

    async def delete_file(self, filename: str) -> dict[str, Any]:
        """Delete a file."""
        filepath = self.base_dir / filename
        if not filepath.exists():
            return {"error": "File not found", "filename": filename}

        filepath.unlink()
        return {"filename": filename, "status": "deleted"}
