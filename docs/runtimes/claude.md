# pga-init-managed

# Claude Code runtime — Personal GRC Agent

Use Claude Code with native skill discovery and governed PGA artifact writes.

**Prerequisites:** [Getting started](../getting-started.md) — bootstrap complete, `spa` on your PATH.

## Setup

```bash
source .venv/bin/activate
spa init --runtime claude
```

This generates:

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Thin shim pointing at `AGENTS.md` |
| `.mcp.json` | Project-scope MCP registration for `pga-governed` |

Skills under `skills/` are **auto-discovered** via `SKILL.md` frontmatter (AgentSkills spec).

Restart Claude Code after init so `.mcp.json` is picked up.

## Using PGA in Claude Code

Claude Code discovers `skills/*/SKILL.md` natively for exploration and drafting guidance. For **verifier-gated outputs** — tickets, redlines, evidence packs, crosswalks — use **`pga-governed`** MCP or `spa run-skill` in the terminal. Direct artifact writes bypass verifiers and the audit chain.

Example workflow:

```bash
spa ingest inbox/my-meeting-notes.md
spa run-skill policy-redline --input change-request.md
spa proposals list
```

## Governance

MCP tools enforce A0–A5 gates. Human-gate tools (`pga_proposals_approve`, `pga_proposals_reject`) require `confirm: true`.

## Verify setup

```bash
spa init --runtime claude --check
make selftest
spa audit verify
```

## Limitations

- Restart Claude Code after editing `.mcp.json`.
- Managed files include `# pga-init-managed` — use `spa init --runtime claude --force` to overwrite local edits.

## See also

- [Getting started](../getting-started.md)
- [AGENTS.md](../../AGENTS.md)
