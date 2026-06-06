#!/usr/bin/env bash
# Runtime install hook — default Hermes Agent; swappable via agent/runtime.config.yaml.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_CONFIG="$ROOT/agent/runtime.config.yaml"

if [[ ! -f "$RUNTIME_CONFIG" ]]; then
  echo "[install] No runtime.config.yaml found; skipping runtime install"
  exit 0
fi

RUNTIME=$(python3 -c "
import yaml, sys
with open('$RUNTIME_CONFIG') as f:
    cfg = yaml.safe_load(f)
print(cfg.get('runtime', 'hermes'))
" 2>/dev/null || echo "hermes")

echo "[install] Configured runtime: $RUNTIME"

case "$RUNTIME" in
  hermes)
    if command -v hermes >/dev/null 2>&1; then
      echo "[install] Hermes Agent already installed: $(hermes --version 2>/dev/null || echo ok)"
    else
      echo "[install] Hermes Agent not found locally."
      echo "[install] Install: curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash"
      echo "[install] Then wire this repo: ./scripts/setup-hermes.sh"
      echo "[install] MVP skills run via 'spa' CLI without Hermes; runtime is swappable."
    fi
    ;;
  *)
    echo "[install] Custom runtime '$RUNTIME' — ensure it is installed per agent/runtime.config.yaml"
    ;;
esac

exit 0
