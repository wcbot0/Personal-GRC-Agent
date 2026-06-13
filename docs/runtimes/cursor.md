# pga-init-managed

# Cursor runtime — Personal GRC Agent

Use Cursor as your AI assistant with the same governed PGA pipeline as the CLI.

**Prerequisites:** [Getting started](../getting-started.md) — bootstrap complete, `spa` on your PATH.

## Setup

```bash
source .venv/bin/activate
spa init --runtime cursor
```

This generates:

| File | Purpose |
|------|---------|
| `.cursor/mcp.json` | Registers `pga-governed` MCP (`spa mcp serve`) |
| `.cursor/rules/pga-runtime.mdc` | Points agents at `AGENTS.md` and governed MCP |

Open the repo root in Cursor so workspace rules and `AGENTS.md` load automatically.

## Using PGA in Cursor

Cursor loads rules from `.cursor/rules/` and `AGENTS.md`. For auditable work — ingest, skills, proposals, audit — use **`pga-governed`** MCP tools or run `spa` in the terminal. Do not hand-write skill JSON when verifiers and audit matter.

Example prompts:

- "Ingest `inbox/my-meeting-notes.md` via governed MCP"
- "Run the csf-crosswalk skill on this vendor artifact"
- "List pending CPOs and show me what needs approval"

## Governance

All MCP tool calls pass ToolGuard and append to the hash-chained audit log. Approve and reject actions require `confirm: true` — Cursor must surface these to you before execution.

## Verify setup

```bash
spa init --runtime cursor --check   # detect stale or missing glue files
make selftest                       # health checks
spa audit verify                    # confirm audit chain
```

If MCP tools do not appear, confirm `.cursor/mcp.json` exists and restart Cursor. Run `spa mcp serve` manually from the repo root to test the server.

## Limitations

- Re-run `spa init --runtime cursor --check` after upgrading PGA to detect stale configuration.
- Use `spa init --runtime cursor --force` to overwrite locally edited managed files.

## See also

- [Getting started](../getting-started.md) — install, first workflow, troubleshooting
- [AGENTS.md](../../AGENTS.md) — path rules and skill routing for AI assistants
