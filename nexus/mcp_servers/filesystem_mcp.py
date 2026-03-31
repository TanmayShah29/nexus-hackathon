"""
filesystem_mcp.py — Filesystem MCP (local file read/write)
"""

from pathlib import Path
from typing import Any


from nexus.config import get_demo_mode
DEMO_MODE = get_demo_mode()


class FilesystemMCP:
    """
    Local filesystem operations.
    """

    def __init__(self, base_dir: str = "/tmp/nexus_files"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, filename: str) -> Path:
        """Resolve and validate path to prevent traversal attacks."""
        path = (self.base_dir / filename).resolve()
        if not str(path).startswith(str(self.base_dir.resolve())):
            raise ValueError(f"Access denied: {filename} is outside base directory")
        return path

    async def read_file(self, filename: str) -> dict[str, Any]:
        """Read a file."""
        try:
            filepath = self._safe_path(filename)
            if not filepath.exists():
                return {"error": "File not found", "filename": filename}

            content = filepath.read_text()
            return {"filename": filename, "content": content}
        except Exception as e:
            return {"error": str(e), "filename": filename}

    async def write_file(self, filename: str, content: str) -> dict[str, Any]:
        """Write content to a file."""
        try:
            filepath = self._safe_path(filename)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content)
            return {"filename": filename, "status": "written"}
        except Exception as e:
            return {"error": str(e), "filename": filename}

    async def list_files(self, pattern: str = "*") -> list[str]:
        """List files matching pattern."""
        try:
            # We don't use _safe_path here directly but we ensure globbing is safe
            return [
                str(p.name)
                for p in self.base_dir.glob(pattern)
                if str(p.resolve()).startswith(str(self.base_dir.resolve()))
            ]
        except Exception:
            return []

    async def delete_file(self, filename: str) -> dict[str, Any]:
        """Delete a file."""
        try:
            filepath = self._safe_path(filename)
            if not filepath.exists():
                return {"error": "File not found", "filename": filename}

            filepath.unlink()
            return {"filename": filename, "status": "deleted"}
        except Exception as e:
            return {"error": str(e), "filename": filename}
