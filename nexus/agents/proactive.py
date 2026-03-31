"""
proactive.py — Proactive Suggestion System

Analyzes user behavior and generates proactive suggestions
that help users before they even ask.
"""

import time
from collections import defaultdict

# Simple in-memory store for demo (would be Firestore in production)
_session_store: dict[str, dict] = defaultdict(
    lambda: {
        "requests": [],
        "last_request_time": None,
        "total_requests": 0,
        "last_agent": None,
        "context": [],
    }
)


class ProactiveEngine:
    """
    Generates proactive suggestions based on user behavior patterns.
    Tracks session state and provides intelligent follow-ups.
    """

    # Time thresholds (in seconds)
    IDLE_WARNING = 2 * 60 * 60  # 2 hours
    LONG_SESSION = 60 * 60  # 1 hour

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.session = _session_store[session_id]

    def record_request(self, prompt: str, agent: str, result: str):
        """Record a request to build behavior profile."""
        now = time.time()

        self.session["requests"].append(
            {
                "prompt": prompt,
                "agent": agent,
                "timestamp": now,
            }
        )

        # Keep only last 10 requests
        self.session["requests"] = self.session["requests"][-10:]

        # Update stats
        if self.session["last_request_time"]:
            idle_time = now - self.session["last_request_time"]
            self.session["idle_time"] = idle_time

        self.session["last_request_time"] = now
        self.session["total_requests"] += 1
        self.session["last_agent"] = agent
        self.session["context"].append(prompt[:100])
        self.session["context"] = self.session["context"][-5:]

    def generate_suggestions(self, current_agent: str, prompt: str) -> list[dict]:
        """Generate proactive suggestions based on behavior analysis."""
        suggestions = []

        # Suggest break after long sessions
        if self._should_suggest_break():
            suggestions.append(
                {
                    "label": "Take a break",
                    "prompt": "What are your scheduled breaks today?",
                    "agent_hint": "scheduler",
                    "trigger": "long_session",
                }
            )

        # Suggest review after research
        if current_agent == "research" and self._recently_researched():
            suggestions.append(
                {
                    "label": "Review notes",
                    "prompt": "Show me my recent research notes",
                    "agent_hint": "notes",
                    "trigger": "research_followup",
                }
            )

        # Suggest planning after morning
        if self._is_morning() and self.session.get("total_requests", 0) < 3:
            suggestions.append(
                {
                    "label": "Plan your day",
                    "prompt": "Create a daily plan with focus blocks",
                    "agent_hint": "scheduler",
                    "trigger": "morning_greeting",
                }
            )

        # Suggest task review after memory
        if current_agent == "memory":
            suggestions.append(
                {
                    "label": "Review tasks",
                    "prompt": "Show my pending tasks",
                    "agent_hint": "tasks",
                    "trigger": "memory_followup",
                }
            )

        # Suggest saving after getting results
        if self._has_useful_result() and current_agent != "notes":
            suggestions.append(
                {
                    "label": "Save for later",
                    "prompt": "Summarize and save this to my notes",
                    "agent_hint": "notes",
                    "trigger": "save_opportunity",
                }
            )

        # Deadline check suggestion
        if self._approaching_deadline():
            suggestions.append(
                {
                    "label": "Check deadlines",
                    "prompt": "What are my upcoming deadlines?",
                    "agent_hint": "scheduler",
                    "trigger": "deadline_warning",
                }
            )

        # Always suggest at least one relevant follow-up
        if not suggestions:
            suggestions = self._get_default_suggestions(current_agent)

        # Limit to 3 suggestions
        return suggestions[:3]

    def _should_suggest_break(self) -> bool:
        """Check if user has been active for a long time."""
        idle = self.session.get("idle_time", 0)
        return idle > self.LONG_SESSION and self.session.get("total_requests", 0) > 3

    def _recently_researched(self) -> bool:
        """Check if user recently did research."""
        requests = self.session.get("requests", [])
        return any(r.get("agent") == "research" for r in requests[-3:])

    def _is_morning(self) -> bool:
        """Check if it's morning hours (6am - 12pm)."""
        from datetime import datetime

        hour = datetime.now().hour
        return 6 <= hour < 12

    def _has_useful_result(self) -> bool:
        """Check if recent results are worth saving."""
        requests = self.session.get("requests", [])
        if not requests:
            return False

        valuable_agents = ["research", "scheduler", "tasks"]
        return any(r.get("agent") in valuable_agents for r in requests[-2:])

    def _approaching_deadline(self) -> bool:
        """Check if there might be approaching deadlines (heuristic)."""
        context = self.session.get("context", [])
        keywords = ["deadline", "due", "exam", "interview", "meeting"]
        return any(any(kw in c.lower() for kw in keywords) for c in context)

    def _get_default_suggestions(self, current_agent: str) -> list[dict]:
        """Get default suggestions based on current agent."""
        defaults = {
            "research": [
                {
                    "label": "Save notes",
                    "prompt": "Save this to notes",
                    "agent_hint": "notes",
                },
                {
                    "label": "Plan study",
                    "prompt": "Create a study plan",
                    "agent_hint": "scheduler",
                },
            ],
            "scheduler": [
                {
                    "label": "Check tasks",
                    "prompt": "Show my tasks",
                    "agent_hint": "tasks",
                },
                {
                    "label": "Add break",
                    "prompt": "Add a break between tasks",
                    "agent_hint": "scheduler",
                },
            ],
            "tasks": [
                {
                    "label": "Check calendar",
                    "prompt": "What's on my calendar?",
                    "agent_hint": "scheduler",
                },
                {
                    "label": "Prioritize",
                    "prompt": "Help me prioritize tasks",
                    "agent_hint": "tasks",
                },
            ],
            "notes": [
                {
                    "label": "Search notes",
                    "prompt": "Find notes about something",
                    "agent_hint": "notes",
                },
            ],
            "memory": [
                {
                    "label": "Show profile",
                    "prompt": "What do you know about me?",
                    "agent_hint": "memory",
                },
            ],
        }
        return defaults.get(
            current_agent,
            [
                {
                    "label": "Help",
                    "prompt": "What can you help me with?",
                    "agent_hint": "orchestrator",
                },
            ],
        )

    def get_session_summary(self) -> dict:
        """Get summary of user session for debugging."""
        return {
            "total_requests": self.session.get("total_requests", 0),
            "last_agent": self.session.get("last_agent"),
            "context": self.session.get("context", []),
        }


def get_proactive_engine(session_id: str) -> ProactiveEngine:
    """Get or create a proactive engine for a session."""
    return ProactiveEngine(session_id)
