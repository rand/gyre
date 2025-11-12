#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PY="$ROOT/.venv/bin/python"

export DSPY_MOCK="${DSPY_MOCK:-1}"
export GYRE_TRANSPORT_FORCE_STUB="${GYRE_TRANSPORT_FORCE_STUB:-1}"

if [ -x "$VENV_PY" ]; then
  echo "[tests] Running pytest via ${VENV_PY}"
  exec "$VENV_PY" -m pytest -q
fi

echo "[tests] No local .venv detected; falling back to uv (requires working uv + network)"
CACHE_DIR="$ROOT/.uv-cache"
mkdir -p "$CACHE_DIR"
UV_CACHE_DIR="$CACHE_DIR" uv run pytest -q
