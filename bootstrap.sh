#!/usr/bin/env bash
# Idempotent bootstrap: venv, deps, docker services, seed brain, selftest.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

log() { echo "[bootstrap] $*"; }

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

docker_ready() {
  docker info >/dev/null 2>&1
}

require_cmd python3
require_cmd docker
require_cmd git

# Ensure local state directories exist (gitignored)
mkdir -p \
  secrets \
  workspace/.data \
  workspace/drafts \
  workspace/proposals \
  governance/audit-logs \
  governance/approval-queue \
  inbox \
  brain/03-policies/proposals \
  brain/evidence

touch inbox/.gitkeep workspace/drafts/.gitkeep workspace/proposals/.gitkeep

# Python virtual environment — recreate if missing or relocated (stale paths in pyvenv.cfg)
VENV="$ROOT/.venv"
VENV_PYTHON="$VENV/bin/python"
VENV_STALE=0
if [[ -d "$VENV" ]]; then
  if [[ ! -x "$VENV_PYTHON" ]]; then
    VENV_STALE=1
  elif [[ -f "$VENV/pyvenv.cfg" ]] && ! grep -qF "$VENV" "$VENV/pyvenv.cfg"; then
    log "Virtualenv was created at a different path; recreating"
    VENV_STALE=1
  fi
fi

if [[ ! -d "$VENV" ]] || [[ "$VENV_STALE" -eq 1 ]]; then
  if [[ "$VENV_STALE" -eq 1 ]]; then
    rm -rf "$VENV"
  fi
  log "Creating virtual environment"
  python3 -m venv "$VENV"
fi

"$VENV_PYTHON" -m pip install --upgrade pip -q
"$VENV_PYTHON" -m pip install -e . -q

# Environment file
if [[ ! -f .env ]]; then
  log "Creating .env from .env.example"
  cp .env.example .env
fi

# Docker services (Qdrant + local embedding model)
if docker_ready; then
  log "Starting Docker services (Qdrant + embeddings)"
  docker compose up -d

  log "Waiting for Qdrant health"
  for i in $(seq 1 30); do
    if curl -sf http://localhost:6333/healthz >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done

  log "Waiting for embedding service (may take a few minutes on first pull)"
  for i in $(seq 1 60); do
    if curl -sf http://localhost:8080/health >/dev/null 2>&1; then
      break
    fi
    sleep 5
  done
else
  log "WARNING: Docker daemon not running — skipping Qdrant/embeddings"
  log "Start Docker Desktop, then run: docker compose up -d && make seed"
fi

# Seed brain into vector DB
log "Seeding brain knowledge base"
"$VENV_PYTHON" scripts/seed_brain.py || log "Seed skipped (services may still be starting)"

log "Running selftest"
make selftest

# Optional Hermes Agent: install, wire MCP, configure model (after spa is verified)
if [[ -x scripts/install.sh ]]; then
  log "Optional Hermes Agent setup"
  ./scripts/install.sh --interactive || log "Hermes setup skipped or partial (spa CLI is ready)"
fi

log "Bootstrap complete. See README.md for quickstart."
