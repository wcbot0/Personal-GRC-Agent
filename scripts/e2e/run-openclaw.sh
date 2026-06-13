#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/_common.sh"
e2e_run openclaw openclaw
