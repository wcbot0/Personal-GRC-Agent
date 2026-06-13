# pga-init-managed

# Hermes runtime — Personal GRC Agent

## Setup

```bash
./bootstrap.sh          # includes optional Hermes wiring
./scripts/setup-hermes.sh
# or
spa init --runtime hermes   # runs setup-hermes.sh + writes this doc
```

Registers **`pga-governed`** in `~/.hermes/config.yaml` (ToolGuard + audit). Legacy writable filesystem mounts are removed on re-run.

## Skills

Hermes loads `AGENTS.md` from the repo root. Run skills via **`pga-governed`** MCP or `spa run-skill`.

## Governance

Prefer governed MCP over chat file writes for ingest, skills, proposals, and audit. Approve/reject requires human confirmation in the client.

## E2E

```bash
./scripts/e2e/run-hermes.sh
```

## Limitations

- Requires Hermes installed separately (`hermes setup` first).
- `setup-hermes.sh` modifies `~/.hermes/config.yaml` (user-level, not committed).
- Without `hermes` on PATH, E2E uses MCP stdio and prints `SKIPPED-RUNTIME-NATIVE`.
