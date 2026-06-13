#!/usr/bin/env bash
# Shared helpers for runtime E2E scripts.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_PYTHON="${VENV_PYTHON:-$ROOT/.venv/bin/python}"

e2e_run() {
  local runtime="$1"
  local native_cmd="${2:-}"

  if [[ -n "$native_cmd" ]] && command -v "${native_cmd%% *}" >/dev/null 2>&1; then
    echo "[e2e] native runtime available: $native_cmd"
    cd "$ROOT"
    "$ROOT/.venv/bin/spa" init --runtime "$runtime" --check >/dev/null 2>&1 || "$ROOT/.venv/bin/spa" init --runtime "$runtime"
  else
    echo "SKIPPED-RUNTIME-NATIVE"
  fi

  cd "$ROOT"
  if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "E2E FAILED: bootstrap required (.venv missing)" >&2
    return 1
  fi

  SPA_NO_LLM=1 "$VENV_PYTHON" "$ROOT/scripts/e2e/mcp_scenario.py" --runtime "$runtime"
}
