"""
tools_agent.py — NEXUS Tools Agent (Arbiter for Utilities)
"""

import asyncio
import logging
import json
import os
import importlib
import inspect

from nexus.models.schemas import AgentResult
from nexus.agents.base import BaseAgent
from nexus.agents.blackboard import Blackboard

logger = logging.getLogger("nexus")


class ToolsAgent(BaseAgent):
    """
    Arbiter for specialized utility APIs.
    Dynamically discovers and routes to all available MCP servers.
    """

    def __init__(self, blackboard: Blackboard):
        super().__init__(name="tools", blackboard=blackboard)
        self._registry = {}
        self._load_mcp_servers()

    def _load_mcp_servers(self):
        """Discovers all MCP servers in the nexus/mcp_servers directory."""
        import os
        import importlib
        import inspect

        mcp_dir = os.path.dirname(__file__).replace("agents", "mcp_servers")
        for filename in os.listdir(mcp_dir):
            if filename.endswith("_mcp.py"):
                module_name = f"nexus.mcp_servers.{filename[:-3]}"
                try:
                    module = importlib.import_module(module_name)
                    for name, obj in inspect.getmembers(module):
                        if (
                            inspect.isclass(obj)
                            and name.endswith("MCP")
                            and name != "BaseMCP"
                        ):
                            # Instantiate and register
                            self._registry[filename[:-7]] = obj()
                            logger.info(f"ToolsAgent | Registered {filename[:-7]} MCP")
                except Exception as e:
                    logger.error(f"ToolsAgent | Failed to load {filename}: {e}")

    async def think(self, goal: str) -> AgentResult:
        self.trace(f"Analyzing utility requirement: {goal}", status="running")

        from nexus.agents.gemini_client import get_completion

        # Build dynamic tool manifest for the system prompt
        manifest = []
        for name, instance in self._registry.items():
            methods = [
                m
                for m, _ in inspect.getmembers(instance, predicate=inspect.iscoroutinefunction)
                if not m.startswith("_")
            ]
            manifest.append(f"- {name}: {', '.join(methods)}")

        system_prompt = f"""You are the NEXUS Tools Arbiter. Identify which MCP utilities are needed.
        Available Tools:
        {chr(10).join(manifest)}

        You can call multiple tools if the goal requires it.
        Return ONLY a JSON array of tool calls: 
        [{{"tool": "tool_name", "method": "method_name", "args": {{...}}}}, ...]
        """

        routing_json = await get_completion(system_prompt, f"User Goal: {goal}")

        # Robust JSON extraction
        try:
            if "```json" in routing_json:
                routing_json = routing_json.split("```json")[-1].split("```")[0].strip()

            if not routing_json.startswith("[") and not routing_json.startswith("{"):
                # Basic cleanup
                start_idx = routing_json.find("[")
                end_idx = routing_json.rfind("]")
                if start_idx != -1 and end_idx != -1:
                    routing_json = routing_json[start_idx : end_idx + 1]

            parsed = json.loads(routing_json)
            routes = parsed if isinstance(parsed, list) else [parsed]
        except Exception as e:
            logger.warning(f"ToolsAgent | Dynamic routing failed: {e}. Falling back to memory.")
            return self.create_result(summary="Routing failed", markdown=f"Error: {e}", confidence=0.0)

        async def _call_one(route):
            tool_name = route.get("tool")
            method_name = route.get("method")
            args = route.get("args", {})
            
            mcp = self._registry.get(tool_name)
            if not mcp:
                return {"tool": tool_name, "error": "Tool not found"}

            method = getattr(mcp, method_name, None)
            if not method:
                return {"tool": tool_name, "error": f"Method {method_name} not found"}

            try:
                data = await method(**args)
                return {"tool": tool_name, "data": data}
            except Exception as e:
                logger.error(f"ToolsAgent | {tool_name}.{method_name} failed: {e}")
                return {"tool": tool_name, "error": str(e)}

        self.trace(f"Invoking {len(routes)} specialist interfaces...", status="running")
        results = await asyncio.gather(*[_call_one(r) for r in routes])
        results = [r for r in results if r]

        # Process results
        md = "### Integrated Intelligence Results\n\n"
        success_count = 0
        for resp in results:
            t_name = resp["tool"]
            if "data" in resp:
                success_count += 1
                self.blackboard.set(f"tools.{t_name}.last", resp["data"], agent_id=self.name)
                md += f"#### {t_name.title()}\n```json\n{json.dumps(resp['data'], indent=2)}\n```\n"
            else:
                md += f"#### {t_name.title()} Error\n> {resp['error']}\n"

        self.trace(f"Operations completed. {success_count} successful.", status="done")

        return self.create_result(
            summary=f"Dispatched {len(results)} cognitive tools ({success_count} successful).",
            markdown=md,
            metrics={"tools_called": len(results), "success_count": success_count},
            confidence=0.9 if success_count > 0 else 0.0,
        )
