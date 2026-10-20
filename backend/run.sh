#!/usr/bin/env bash
# Start the live agent backend on your Mac.
set -e
cd "$(dirname "$0")/.."
source ../.hermes/.env 2>/dev/null || true
# Pin to the CLT python that has the deps installed.
# NOTE: bare `python3` resolves to Homebrew's python@3.15 (no uvicorn here) and silently dies.
PY="${PYTHON:-/usr/bin/python3}"
exec "$PY" -m uvicorn backend.app:app --host 0.0.0.0 --port "${AGENT_PORT:-8765}"
