# pga-init-managed

# Cursor runtime — Personal GRC Agent

## Setup

```bash
source .venv/bin/activate
spa init --runtime cursor
```

Generates:

| File | Purpose |
|------|---------|
| `.cursor/mcp.json` | Registers `pga-governed` MCP (`spa mcp serve`) |
| `.cursor/rules/pga-runtime.mdc` | Points agents at `AGENTS.md` and governed MCP |

## Skills

Cursor loads workspace rules from `.cursor/rules/` and `AGENTS.md`. PGA skills run through **`pga-governed`** MCP or the `spa` CLI — not by hand-writing skill JSON.

## Governance

All MCP tool calls pass ToolGuard and append to the hash-chained audit log. A3 approve/reject requires `confirm=true` on the MCP client.

## E2E

```bash
./scripts/e2e/run-cursor.sh
```

## Limitations

- Cursor native binary is optional; without it the E2E script uses the MCP stdio client and prints `SKIPPED-RUNTIME-NATIVE`.
- Re-run `spa init --runtime cursor --check` after upgrading PGA to detect stale glue.
