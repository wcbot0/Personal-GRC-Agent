#!/usr/bin/env bash
# Backup local SPA state (workspace + governance logs) — excludes secrets.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$ROOT/workspace/.data/backup-$STAMP.tar.gz"
EVIDENCE_OUT="$ROOT/workspace/.data/evidence-$STAMP.tar.gz"

VENV_PYTHON="$ROOT/.venv/bin/python"
if [[ -x "$VENV_PYTHON" ]]; then
  PYTHON="$VENV_PYTHON"
else
  PYTHON=python3
fi

FROM_DATE="$(date -u -v-1d +%Y-%m-%d 2>/dev/null || date -u -d '1 day ago' +%Y-%m-%d)"
TO_DATE="$(date -u +%Y-%m-%d)"

mkdir -p "$ROOT/workspace/.data"

if "$PYTHON" -m spa.cli audit verify --dir "$ROOT/governance/audit-logs" >/dev/null 2>&1; then
  echo "Audit chain verification: OK"
else
  echo "Audit chain verification: WARN (legacy or broken chain — see spa audit verify)"
fi

if "$PYTHON" -m spa.cli evidence export --from "$FROM_DATE" --to "$TO_DATE" --output "$EVIDENCE_OUT" --force 2>/dev/null; then
  echo "Evidence export written: $EVIDENCE_OUT"
else
  echo "Evidence export skipped (no audit events in range or spa unavailable)"
fi

tar -czf "$OUT" \
  -C "$ROOT" \
  workspace/drafts \
  workspace/proposals \
  governance/audit-logs \
  governance/approval-queue \
  2>/dev/null || true

echo "Backup written: $OUT"
