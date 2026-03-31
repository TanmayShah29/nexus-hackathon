"""
executor_mcp.py — Python Executor MCP (sandboxed)
"""

import sys
import io
from typing import Any


from nexus.config import get_demo_mode
DEMO_MODE = get_demo_mode()


class ExecutorMCP:
    """
    Sandboxed Python code execution.
    """

    def __init__(
        self, demo_mode: bool = DEMO_MODE, timeout: int = 5, memory_limit_mb: int = 128
    ):
        self.demo_mode = demo_mode
        self.timeout = timeout
        self.memory_limit = memory_limit_mb

    async def execute(self, code: str) -> dict[str, Any]:
        """Execute Python code and return output."""
        return self._execute_sandbox(code)

    def _execute_sandbox(self, code: str) -> dict[str, Any]:
        """Execute in a sandboxed environment."""
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture

        try:
            # Safer restricted execution for hackathon demo
            # We explicitly define allowed builtins and prevent access to __builtins__
            safe_globals = {
                "print": lambda *args: stdout_capture.write(" ".join(map(str, args)) + "\n"),
                "sum": sum,
                "len": len,
                "range": range,
                "int": int,
                "float": float,
                "list": list,
                "dict": dict,
                "__builtins__": {} # Disable access to dangerous builtins like __import__
            }
            exec(code, safe_globals, {})
            output = stdout_capture.getvalue()
            error = stderr_capture.getvalue()
            return {
                "status": "success",
                "output": output,
                "error": error,
            }
        except Exception as e:
            return {
                "status": "error",
                "output": stdout_capture.getvalue(),
                "error": str(e),
            }
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
