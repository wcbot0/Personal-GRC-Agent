#!/usr/bin/env bash
# Backup local SPA state (workspace + governance logs) — excludes secrets.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$ROOT/workspace/.data/backup-$STAMP.tar.gz"

mkdir -p "$ROOT/workspace/.data"
tar -czf "$OUT" \
  -C "$ROOT" \
  workspace/drafts \
  workspace/proposals \
  governance/audit-logs \
  governance/approval-queue \
  2>/dev/null || true

echo "Backup written: $OUT"
