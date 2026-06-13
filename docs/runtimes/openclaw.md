# pga-init-managed

# OpenClaw runtime — Personal GRC Agent

## Setup

```bash
source .venv/bin/activate
spa init --runtime openclaw
```

Generates:

| File | Purpose |
|------|---------|
| `.openclaw/openclaw.json` | Skills load path + `pga-governed` MCP stdio server |
| `docs/runtimes/openclaw.md` | This page |

Workspace skills load from `skills/` (`SKILL.md` per AgentSkills spec).

## Skills

OpenClaw discovers `skills/**/SKILL.md` under configured roots. Governed artifact writes still go through **`pga-governed`** MCP or `spa` CLI.

## Governance

MCP server runs `spa mcp serve` with repo as cwd — all writes audited and policy-gated.

## E2E

```bash
./scripts/e2e/run-openclaw.sh
```

## Limitations

- OpenClaw Gateway must reload config after init (new session).
- Without `openclaw` CLI on PATH, E2E uses MCP stdio fallback (`SKIPPED-RUNTIME-NATIVE`).
