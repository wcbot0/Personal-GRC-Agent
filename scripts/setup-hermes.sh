#!/usr/bin/env bash
# Wire this PGA repo into Hermes Agent (MCP filesystem + workspace rules).
# Idempotent: safe to re-run; updates paths if the repo was moved.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MCP_NAME="pga-filesystem"
VENV_PYTHON="$ROOT/.venv/bin/python"

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

log "Hermes: $(hermes --version 2>/dev/null | head -1 || echo installed)"
log "Repo:  $ROOT"

"$VENV_PYTHON" - <<'PY' "$ROOT" "$MCP_NAME"
import sys
from pathlib import Path

import yaml

root = Path(sys.argv[1])
mcp_name = sys.argv[2]
config_path = Path.home() / ".hermes" / "config.yaml"

if not config_path.exists():
    print(f"[setup-hermes] Hermes config not found at {config_path}", file=sys.stderr)
    print("[setup-hermes] Run: hermes setup", file=sys.stderr)
    sys.exit(1)

cfg = yaml.safe_load(config_path.read_text()) or {}
servers = cfg.setdefault("mcp_servers", {})
servers[mcp_name] = {
    "command": "npx",
    "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        str(root / "brain"),
        str(root / "inbox"),
        str(root / "workspace" / "drafts"),
    ],
    "enabled": True,
}
config_path.write_text(yaml.dump(cfg, default_flow_style=False, sort_keys=False))
print(f"[setup-hermes] Wrote MCP server '{mcp_name}' to {config_path}")
PY

if hermes mcp test "$MCP_NAME" 2>/dev/null; then
  log "MCP connection test passed"
else
  log "MCP test did not pass yet — try: hermes mcp test $MCP_NAME"
  log "(First run may download the MCP package via npx; retry after a minute.)"
fi

cat <<EOF

Setup complete. Start a session from this repo:

  cd "$ROOT"
  hermes chat

Hermes auto-loads AGENTS.md from the repo root (persona + draft rules).
For governed skill runs with audit + verifiers, use the spa CLI:

  source .venv/bin/activate
  spa ingest inbox/my-notes.md
  spa run-skill meeting-synth --input evals/fixtures/meeting_sample.md

Configure your LLM if you have not already:

  hermes model          # pick provider + model
  hermes doctor         # diagnose missing deps

EOF
