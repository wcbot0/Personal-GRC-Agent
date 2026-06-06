#!/usr/bin/env bash
# Prompt-injection corpus runner for ingestion paths.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VENV_PYTHON="$ROOT/.venv/bin/python"
if [[ -x "$VENV_PYTHON" ]]; then
  PYTHON="$VENV_PYTHON"
else
  PYTHON=python3
fi

exec "$PYTHON" -m spa.testing.redteam "$@"
