#!/usr/bin/env bash
# Wire this PGA repo into Hermes Agent (governed MCP + read-only brain browse).
# Idempotent: safe to re-run; updates paths if the repo was moved.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FS_MCP_NAME="pga-filesystem"
GOV_MCP_NAME="pga-governed"
VENV_PYTHON="$ROOT/.venv/bin/python"
SPA_BIN="$ROOT/.venv/bin/spa"

log() { echo "[setup-hermes] $*"; }

if ! command -v hermes >/dev/null 2>&1; then
  echo "Hermes Agent is not installed." >&2
  echo "Install: curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash" >&2
  echo "Then reload your shell and re-run: ./scripts/setup-hermes.sh" >&2
  exit 1
fi

if ! command -v npx >/dev/null 2>&1; then
  echo "Node.js / npx is required for the filesystem MCP server." >&2
  echo "Hermes installer usually includes Node; try: hermes postinstall" >&2
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

"$VENV_PYTHON" - <<'PY' "$ROOT" "$FS_MCP_NAME" "$GOV_MCP_NAME" "$SPA_BIN"
import sys
from pathlib import Path

import yaml

root = Path(sys.argv[1])
fs_mcp_name = sys.argv[2]
gov_mcp_name = sys.argv[3]
spa_bin = sys.argv[4]
config_path = Path.home() / ".hermes" / "config.yaml"

if not config_path.exists():
    print(f"[setup-hermes] Hermes config not found at {config_path}", file=sys.stderr)
    print("[setup-hermes] Run: hermes setup", file=sys.stderr)
    sys.exit(1)

cfg = yaml.safe_load(config_path.read_text()) or {}
servers = cfg.setdefault("mcp_servers", {})

# Read-only brain browse (demoted from full write mounts)
servers[fs_mcp_name] = {
    "command": "npx",
    "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        str(root / "brain"),
    ],
    "enabled": True,
}

# Governed PGA tools — ingest, skills, proposals, audit (ToolGuard + verifiers)
servers[gov_mcp_name] = {
    "command": spa_bin,
    "args": ["mcp", "serve"],
    "cwd": str(root),
    "enabled": True,
}

config_path.write_text(yaml.dump(cfg, default_flow_style=False, sort_keys=False))
print(f"[setup-hermes] Wrote MCP servers '{fs_mcp_name}' (brain read-only) and '{gov_mcp_name}' (governed) to {config_path}")
PY

if hermes mcp test "$GOV_MCP_NAME" 2>/dev/null; then
  log "Governed MCP connection test passed"
else
  log "Governed MCP test did not pass yet — try: hermes mcp test $GOV_MCP_NAME"
fi

if hermes mcp test "$FS_MCP_NAME" 2>/dev/null; then
  log "Filesystem MCP connection test passed"
else
  log "Filesystem MCP test did not pass yet — try: hermes mcp test $FS_MCP_NAME"
fi

cat <<EOF

Setup complete. Start a session from this repo:

  cd "$ROOT"
  hermes chat

Hermes auto-loads AGENTS.md from the repo root (persona + draft rules).

**Prefer the governed MCP server (\`$GOV_MCP_NAME\`)** for ingest, skills, proposals, and audit —
it routes through ToolGuard and the hash-chained audit trail.

Read-only \`$FS_MCP_NAME\` mounts \`brain/\` for browsing only.

For CLI batch work:

  source .venv/bin/activate
  spa ingest inbox/my-notes.md
  spa run-skill meeting-synth --input evals/fixtures/meeting_sample.md

Configure your LLM if you have not already:

  hermes model          # pick provider + model
  hermes doctor         # diagnose missing deps

EOF
