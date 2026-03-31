#!/bin/bash
# run.sh — NEXUS Quick Start
# Usage: ./run.sh [port]
# Must be run from the repo root.

set -e

PORT=${1:-8000}
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║  NEXUS OS — Multi-Agent Productivity     ║"
echo "╚══════════════════════════════════════════╝"
echo "  Port : $PORT"
echo ""

# Locate virtualenv — support both .venv/ (repo root) and nexus/venv/
if [ -d "$REPO_ROOT/.venv" ]; then
    VENV="$REPO_ROOT/.venv"
elif [ -d "$REPO_ROOT/nexus/venv" ]; then
    VENV="$REPO_ROOT/nexus/venv"
else
    echo "❌  No virtual environment found."
    echo "    Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r nexus/requirements.txt"
    exit 1
fi

source "$VENV/bin/activate"

# Always run from repo root so `nexus` resolves as a Python package
cd "$REPO_ROOT"

echo "✅  Starting NEXUS at http://localhost:$PORT"
echo "    Docs: http://localhost:$PORT/docs"
echo ""

uvicorn nexus.main:app --host 0.0.0.0 --port "$PORT" --reload --reload-dir nexus
