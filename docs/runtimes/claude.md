# pga-init-managed

# Claude Code runtime — Personal GRC Agent

## Setup

```bash
source .venv/bin/activate
spa init --runtime claude
```

Generates:

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Thin shim pointing at `AGENTS.md` |
| `.mcp.json` | Project-scope MCP registration for `pga-governed` |

Skills under `skills/` are **auto-discovered** via `SKILL.md` frontmatter (AgentSkills spec).

## Skills

Claude Code discovers `skills/*/SKILL.md` natively. For verifier-gated outputs (tickets, redlines, evidence), use **`pga-governed`** MCP or `spa run-skill` — not direct artifact writes.

## Governance

MCP tools enforce A0–A5 gates. Human-gate tools (`pga_proposals_approve`, `pga_proposals_reject`) require `confirm=true`.

## E2E

```bash
./scripts/e2e/run-claude.sh
```

## Limitations

- Restart Claude Code after editing `.mcp.json`.
- Managed files include `# pga-init-managed` — use `spa init --runtime claude --force` to overwrite local edits.
