# pga-init-managed

# OpenClaw runtime — Personal GRC Agent

Use OpenClaw with PGA skills discovery and governed MCP artifact writes.

**Prerequisites:** [Getting started](../getting-started.md) — bootstrap complete, `spa` on your PATH.

## Setup

```bash
source .venv/bin/activate
spa init --runtime openclaw
```

This generates:

| File | Purpose |
|------|---------|
| `.openclaw/openclaw.json` | Skills load path + `pga-governed` MCP stdio server |
| `docs/runtimes/openclaw.md` | This page |

Workspace skills load from `skills/` (`SKILL.md` per AgentSkills spec).

Reload OpenClaw Gateway config after init (start a new session).

## Using PGA in OpenClaw

OpenClaw discovers `skills/**/SKILL.md` under configured roots for skill contracts and guidance. **Governed artifact writes** still go through **`pga-governed`** MCP or the `spa` CLI — not ad-hoc file writes.

```bash
spa ingest inbox/my-notes.md
spa run-skill ticket-draft --input gap-description.md
```

## Governance

The MCP server runs `spa mcp serve` with the repo as cwd — all writes are audited and policy-gated.

## Verify setup

```bash
spa init --runtime openclaw --check
make selftest
spa audit verify
```

## Limitations

- OpenClaw Gateway must reload config after init.
- Without the OpenClaw CLI, configure MCP manually using the stdio entry in `.openclaw/openclaw.json`.

## See also

- [Getting started](../getting-started.md)
- [AGENTS.md](../../AGENTS.md)
- [OpenClaw docs](https://docs.openclaw.ai/)
