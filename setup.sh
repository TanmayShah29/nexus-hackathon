#!/bin/bash
# setup.sh — NEXUS First-time Setup
# Usage: ./setup.sh

set -e

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║  NEXUS OS — Setup                        ║"
echo "╚══════════════════════════════════════════╝"
echo ""

cd "$REPO_ROOT"

# Create virtualenv at repo root
if [ ! -d ".venv" ]; then
    echo "📦  Creating virtual environment (.venv)…"
    python3 -m venv .venv
fi

source .venv/bin/activate

echo "📦  Installing Python dependencies…"
pip install -q --upgrade pip
pip install -q -r nexus/requirements.txt

# Create .env from example if missing
if [ ! -f "nexus/.env" ]; then
    echo "📝  Creating nexus/.env from .env.example…"
    cp nexus/.env.example nexus/.env
    echo "    ⚠️  Fill in nexus/.env with your API keys before running in LIVE mode."
fi

# Ensure storage dir exists so Blackboard can write without errors
mkdir -p nexus/storage

echo ""
echo "✅  Setup complete!"
echo ""
echo "  Start NEXUS:      ./run.sh"
echo "  Open app:         http://localhost:8000"
echo "  API docs:         http://localhost:8000/docs"
echo ""
