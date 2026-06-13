#!/usr/bin/env bash
# Wire this PGA repo into Hermes Agent (governed MCP).
# Idempotent: safe to re-run; updates paths if the repo was moved.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GOV_MCP_NAME="pga-governed"
LEGACY_FS_MCP_NAME="pga-filesystem"
VENV_PYTHON="$ROOT/.venv/bin/python"
SPA_BIN="$ROOT/.venv/bin/spa"

log() { echo "[setup-hermes] $*"; }

if ! command -v hermes >/dev/null 2>&1; then
  echo "Hermes Agent is not installed." >&2
  echo "Install: curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash" >&2
  echo "Then reload your shell and re-run: ./scripts/setup-hermes.sh" >&2
  exit 1
fi

if [[ ! -x "$VENV_PYTHON" ]]; then
  log "PGA not bootstrapped yet — run ./bootstrap.sh first"
  exit 1
fi

if [[ ! -x "$SPA_BIN" ]]; then
  log "spa CLI missing — run ./bootstrap.sh or: pip install -e ."
  exit 1
fi

log "Hermes: $(hermes --version 2>/dev/null | head -1 || echo installed)"
log "Repo:  $ROOT"

"$VENV_PYTHON" - <<'PY' "$ROOT" "$GOV_MCP_NAME" "$LEGACY_FS_MCP_NAME" "$SPA_BIN"
import sys
from pathlib import Path

import yaml

root = Path(sys.argv[1])
gov_mcp_name = sys.argv[2]
legacy_fs_mcp_name = sys.argv[3]
spa_bin = sys.argv[4]
config_path = Path.home() / ".hermes" / "config.yaml"

if not config_path.exists():
    print(f"[setup-hermes] Hermes config not found at {config_path}", file=sys.stderr)
    print("[setup-hermes] Run: hermes setup", file=sys.stderr)
    sys.exit(1)

cfg = yaml.safe_load(config_path.read_text()) or {}
servers = cfg.setdefault("mcp_servers", {})

# Legacy filesystem mount exposed write_file/edit_file/move_file — not read-only.
# Remove on every run so Hermes sessions cannot bypass ToolGuard via brain/ writes.
if legacy_fs_mcp_name in servers:
    del servers[legacy_fs_mcp_name]
    print(f"[setup-hermes] Removed legacy MCP server '{legacy_fs_mcp_name}'")

# Governed PGA tools — ingest, skills, proposals, audit (ToolGuard + verifiers)
servers[gov_mcp_name] = {
    "command": spa_bin,
    "args": ["mcp", "serve"],
    "cwd": str(root),
    "enabled": True,
}

config_path.write_text(yaml.dump(cfg, default_flow_style=False, sort_keys=False))
print(f"[setup-hermes] Wrote MCP server '{gov_mcp_name}' (governed) to {config_path}")
PY

if hermes mcp test "$GOV_MCP_NAME" 2>/dev/null; then
  log "Governed MCP connection test passed"
else
  log "Governed MCP test did not pass yet — try: hermes mcp test $GOV_MCP_NAME"
fi

cat <<EOF

Setup complete. Start a session from this repo:

  cd "$ROOT"
  hermes chat

Hermes auto-loads AGENTS.md from the repo root (persona + draft rules).

**Use the governed MCP server (\`$GOV_MCP_NAME\`)** for ingest, skills, proposals, audit, and memory search —
it routes through ToolGuard and the hash-chained audit trail.

Browse \`brain/\` in your editor or via \`pga_memory_search\`; do not mount a raw filesystem MCP (no read-only mode).

For CLI batch work:

  source .venv/bin/activate
  spa ingest inbox/my-notes.md
  spa run-skill meeting-synth --input evals/fixtures/meeting_sample.md

Configure your LLM if you have not already:

  hermes model          # pick provider + model
  hermes doctor         # diagnose missing deps

EOF
