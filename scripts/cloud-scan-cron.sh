#!/usr/bin/env bash
# Cron-friendly wrapper for scheduled cloud findings scans (read-only).
# Register in crontab manually, e.g.:
#   0 6 * * 1 cd /path/to/Personal-GRC-Agent && source .venv/bin/activate && ./scripts/cloud-scan-cron.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source .venv/bin/activate
spa cloud scan "$@"
