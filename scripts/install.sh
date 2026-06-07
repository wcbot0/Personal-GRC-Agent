#!/usr/bin/env bash
# Runtime install hook — default Hermes Agent; swappable via agent/runtime.config.yaml.
#
# Usage:
#   ./scripts/install.sh              # status check only
#   ./scripts/install.sh --interactive # bootstrap end: prompt to install/wire/configure
#   HERMES_BOOTSTRAP=1 ./scripts/install.sh --interactive  # install+wire without prompts
#   HERMES_BOOTSTRAP=0 ./bootstrap.sh                        # skip Hermes phase entirely
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_CONFIG="$ROOT/agent/runtime.config.yaml"
HERMES_INSTALL_URL="https://hermes-agent.nousresearch.com/install.sh"
INTERACTIVE=0

log() { echo "[install] $*"; }

usage() {
  cat <<EOF
Usage: $(basename "$0") [--interactive]

  --interactive   Offer Hermes install, MCP wiring, and model setup (bootstrap end).
                  Respects HERMES_BOOTSTRAP: 0=skip, 1=install without prompts.

Environment:
  HERMES_BOOTSTRAP   0=skip Hermes phase; 1=auto-install+wire (no prompts); unset=prompt if TTY
  CI=true            Always skips Hermes install/wire (spa bootstrap still runs)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --interactive) INTERACTIVE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

is_tty() {
  [[ -t 0 && -t 1 ]]
}

configured_runtime() {
  if [[ ! -f "$RUNTIME_CONFIG" ]]; then
    echo "none"
    return
  fi
  python3 -c "
import yaml
with open('$RUNTIME_CONFIG') as f:
    cfg = yaml.safe_load(f) or {}
print(cfg.get('runtime', 'hermes'))
" 2>/dev/null || echo "hermes"
}

refresh_hermes_path() {
  local d
  for d in "$HOME/.local/bin" "$HOME/.hermes/bin" "$HOME/bin"; do
    if [[ -d "$d" ]]; then
      case ":$PATH:" in
        *":$d:"*) ;;
        *) export PATH="$d:$PATH" ;;
      esac
    fi
  done
}

hermes_available() {
  refresh_hermes_path
  command -v hermes >/dev/null 2>&1
}

hermes_version_line() {
  hermes --version 2>/dev/null | head -1 || echo "installed"
}

should_skip_hermes_bootstrap() {
  [[ "${CI:-}" == "true" ]] && return 0
  [[ "${HERMES_BOOTSTRAP:-}" == "0" ]] && return 0
  return 1
}

prompt_yes_no() {
  local prompt="$1" default="${2:-n}" reply
  if [[ "$default" == "y" ]]; then
    printf '%s [Y/n]: ' "$prompt"
  else
    printf '%s [y/N]: ' "$prompt"
  fi
  read -r reply || reply=""
  if [[ -z "$reply" ]]; then
    reply="$default"
  fi
  case "$(printf '%s' "$reply" | tr '[:upper:]' '[:lower:]')" in
    y|yes) return 0 ;;
    *) return 1 ;;
  esac
}

install_hermes_binary() {
  if ! command -v curl >/dev/null 2>&1; then
    log "curl is required to install Hermes Agent." >&2
    return 1
  fi
  log "Installing Hermes Agent from $HERMES_INSTALL_URL"
  curl -fsSL "$HERMES_INSTALL_URL" | bash
  refresh_hermes_path
  if hermes_available; then
    log "Hermes installed: $(hermes_version_line)"
    return 0
  fi
  log "Hermes install finished but 'hermes' is not on PATH yet."
  log "Open a new shell or run: export PATH=\"\$HOME/.local/bin:\$PATH\""
  log "Then re-run: ./scripts/setup-hermes.sh"
  return 1
}

ensure_hermes_config() {
  local config="$HOME/.hermes/config.yaml"
  if [[ -f "$config" ]]; then
    return 0
  fi
  if ! hermes_available; then
    return 1
  fi
  log "Hermes config not found — running 'hermes setup' to create ~/.hermes/config.yaml"
  if is_tty; then
    hermes setup
  else
    log "Non-interactive shell — run manually: hermes setup"
    return 1
  fi
  [[ -f "$config" ]]
}

wire_hermes_repo() {
  if [[ ! -x "$ROOT/scripts/setup-hermes.sh" ]]; then
    log "setup-hermes.sh not found; skipping MCP wiring"
    return 1
  fi
  "$ROOT/scripts/setup-hermes.sh"
}

maybe_configure_hermes_model() {
  if ! hermes_available; then
    return 0
  fi
  if [[ "${HERMES_BOOTSTRAP:-}" == "1" ]]; then
    log "Skipping model wizard (HERMES_BOOTSTRAP=1). Configure later: hermes model"
    return 0
  fi
  if ! is_tty; then
    log "Configure your LLM later: hermes model  (keys live in ~/.hermes/.env)"
    return 0
  fi
  if prompt_yes_no "Configure Hermes model/provider now?"; then
    hermes model || log "Model setup incomplete — run: hermes model"
  else
    log "Configure later: hermes model  or  hermes doctor"
  fi
}

run_interactive_hermes_bootstrap() {
  local runtime want_install=0

  runtime="$(configured_runtime)"
  log "Configured runtime: $runtime"

  if [[ "$runtime" != "hermes" ]]; then
    log "Runtime is '$runtime' — Hermes bootstrap skipped (see agent/runtime.config.yaml)"
    return 0
  fi

  if should_skip_hermes_bootstrap; then
    log "Hermes bootstrap skipped (CI=true or HERMES_BOOTSTRAP=0)"
    log "Enable later: ./scripts/install.sh --interactive  or  HERMES_BOOTSTRAP=1 ./bootstrap.sh"
    return 0
  fi

  if hermes_available; then
    log "Hermes Agent already installed: $(hermes_version_line)"
  else
    if [[ "${HERMES_BOOTSTRAP:-}" == "1" ]]; then
      want_install=1
    elif is_tty; then
      if prompt_yes_no "Install Hermes Agent (chat runtime)?"; then
        want_install=1
      else
        log "Skipped Hermes install. MVP skills run via 'spa' without Hermes."
        log "Install later: curl -fsSL $HERMES_INSTALL_URL | bash"
        return 0
      fi
    else
      log "Hermes Agent not found (non-interactive). Install later:"
      log "  curl -fsSL $HERMES_INSTALL_URL | bash"
      log "  ./scripts/setup-hermes.sh"
      return 0
    fi

    if [[ "$want_install" -eq 1 ]]; then
      install_hermes_binary || return 0
    fi
  fi

  if ! hermes_available; then
    return 0
  fi

  if ! ensure_hermes_config; then
    log "Complete Hermes setup, then run: ./scripts/setup-hermes.sh"
    return 0
  fi

  wire_hermes_repo || true
  maybe_configure_hermes_model

  cat <<EOF

Hermes is wired to this repo. Start chat from the repo root:

  cd "$ROOT"
  hermes chat

Governed skill runs (audit + verifiers): use the spa CLI (source .venv/bin/activate).

EOF
}

run_status_check() {
  local runtime
  runtime="$(configured_runtime)"
  log "Configured runtime: $runtime"

  case "$runtime" in
    hermes)
      if hermes_available; then
        log "Hermes Agent installed: $(hermes_version_line)"
      else
        log "Hermes Agent not found locally."
        log "Install: curl -fsSL $HERMES_INSTALL_URL | bash"
        log "Then wire this repo: ./scripts/setup-hermes.sh"
        log "Or run bootstrap with prompts: ./bootstrap.sh"
      fi
      ;;
    none)
      log "No runtime.config.yaml — skipping runtime check"
      ;;
    *)
      log "Custom runtime '$runtime' — ensure it is installed per agent/runtime.config.yaml"
      ;;
  esac
}

if [[ "$INTERACTIVE" -eq 1 ]]; then
  run_interactive_hermes_bootstrap
else
  run_status_check
fi

exit 0
