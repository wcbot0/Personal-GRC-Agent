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

# Python virtual environment
if [[ ! -d .venv ]]; then
  log "Creating virtual environment"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip -q
pip install -e . -q

# Environment file
if [[ ! -f .env ]]; then
  log "Creating .env from .env.example"
  cp .env.example .env
fi

# Docker services (Qdrant + local embedding model)
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

# Runtime install hook (Hermes default; swappable via agent/runtime.config.yaml)
if [[ -x scripts/install.sh ]]; then
  log "Running runtime install hook"
  ./scripts/install.sh || log "Runtime install hook skipped or partial (OK for stub mode)"
fi

# Seed brain into vector DB
log "Seeding brain knowledge base"
python scripts/seed_brain.py || log "Seed skipped (services may still be starting)"

log "Running selftest"
make selftest

log "Bootstrap complete. See README.md for quickstart."
