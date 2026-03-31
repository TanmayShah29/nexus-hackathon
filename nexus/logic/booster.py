"""
logic/booster.py — NEXUS Booster (Fixed)

FIX: datetime.now().astimezone() returns local time with timezone offset,
     so deployed UTC servers display the user's tz if Accept-Timezone header
     is provided in future. For now we use local server time with tz label.
"""
from __future__ import annotations

import operator
import re
from datetime import datetime, timezone
from typing import Callable, Optional


class NEXUSBooster:
    """
    Zero-latency local logic engine.
    Intercepts deterministic queries before they hit the LLM.
    """

    _safe_operators: dict[str, Callable] = {
        "+": operator.add,
        "-": operator.sub,
        "*": operator.mul,
        "/": operator.truediv,
        "**": operator.pow,
        "%": operator.mod,
    }

    @staticmethod
    def _safe_eval(expr: str) -> Optional[float]:
        """Recursive-descent math parser — no eval()."""
        try:
            expr = expr.strip()

            def parse_term():
                nonlocal expr
                expr = expr.lstrip()
                if expr.startswith("("):
                    expr = expr[1:]
                    result = parse_expr()
                    if expr and expr[0] == ")":
                        expr = expr[1:]
                    return result
                if expr and expr[0] == "-":
                    expr = expr[1:]
                    return -parse_term()
                num_str = ""
                while expr and (expr[0].isdigit() or expr[0] == "."):
                    num_str += expr[0]
                    expr = expr[1:]
                return float(num_str) if num_str else None

            def parse_power():
                nonlocal expr
                left = parse_term()
                if left is None:
                    return None
                expr = expr.lstrip()
                if expr and expr[:2] == "**":
                    expr = expr[2:]
                    right = parse_power()
                    return operator.pow(left, right) if right is not None else None
                return left

            def parse_factor():
                nonlocal expr
                left = parse_power()
                if left is None:
                    return None
                expr = expr.lstrip()
                while expr and expr[0] in "*/%":
                    op = expr[0]
                    expr = expr[1:]
                    right = parse_power()
                    if right is None:
                        return None
                    if op == "*":
                        left = operator.mul(left, right)
                    elif op == "/":
                        if right == 0:
                            return None
                        left = operator.truediv(left, right)
                    elif op == "%":
                        left = operator.mod(left, right)
                return left

            def parse_expr():
                nonlocal expr
                left = parse_factor()
                if left is None:
                    return None
                expr = expr.lstrip()
                while expr and expr[0] in "+-":
                    op = expr[0]
                    expr = expr[1:]
                    right = parse_factor()
                    if right is None:
                        return None
                    left = operator.add(left, right) if op == "+" else operator.sub(left, right)
                return left

            result = parse_expr()
            return float(result) if result is not None and not expr.strip() else None
        except (ValueError, TypeError, ZeroDivisionError):
            return None

    @staticmethod
    def try_boost(prompt: str) -> Optional[dict]:
        clean = prompt.lower().strip()

        # 1. Table formatting
        if "format as table" in clean or "make a table" in clean:
            items = re.findall(r"\[(.*?)\]", prompt)
            if items:
                rows = items[0].split(",")
                table = "| Key | Value |\n|---|---|\n"
                for i, r in enumerate(rows):
                    table += f"| Item {i + 1} | {r.strip()} |\n"
                return {
                    "agent": "booster",
                    "agent_display_name": "NEXUS Booster",
                    "summary": "Formatted data into Markdown table locally.",
                    "markdown_content": f"### Local Transformation\n\n{table}\n\n*<1ms.*",
                    "tool_calls": [],
                    "suggestions": [{"label": "Export to CSV", "prompt": "Export this table to CSV"}],
                }

        # 2. Math evaluation
        math_keywords = ["calculate", "evaluate", "solve", "math", "compute"]
        is_math = any(kw in clean for kw in math_keywords)
        math_content = re.sub(r"[a-z\s?]", "", clean)
        has_op = any(op in math_content for op in ["+", "*", "/", "^"]) or (
            math_content.count("-") == 1 and not math_content.startswith("-")
        )
        if (is_math or (math_content and len(math_content) / max(len(clean), 1) > 0.8)) and has_op:
            if all(c in "0123456789.+-*/^()" for c in math_content):
                expr = math_content.replace("^", "**")
                result = NEXUSBooster._safe_eval(expr)
                if result is not None:
                    return {
                        "agent": "booster",
                        "agent_display_name": "NEXUS Booster",
                        "summary": f"Calculated: {result}",
                        "markdown_content": f"### Math\n\n`{math_content}` = `{result}`\n\n*<0.1ms*",
                        "tool_calls": [],
                    }

        # 3. Time & date
        # FIX: Use UTC-aware now() with local timezone label
        time_pat = r"\b(what time|current time|what'?s the time|what is the time)\b"
        date_pat = r"\b(what date|today'?s date|what day is it|what is the date)\b"
        if re.search(time_pat, clean) or re.search(date_pat, clean):
            now = datetime.now(timezone.utc).astimezone()  # local tz
            if re.search(time_pat, clean):
                resp = f"The current time is **{now.strftime('%I:%M %p %Z')}**."
            else:
                resp = f"Today is **{now.strftime('%A, %B %d, %Y')}**."
            return {
                "agent": "booster",
                "agent_display_name": "NEXUS Booster",
                "summary": "Retrieved system time/date locally.",
                "markdown_content": f"### System Time\n\n{resp}\n\n*Resolved locally.*",
                "tool_calls": [],
                "suggestions": [
                    {"label": "Add to calendar", "prompt": "Schedule something for today"},
                    {"label": "Check weather", "prompt": "What is the weather like right now?"},
                ],
            }

        return None
