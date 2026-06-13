# pga-init-managed

# ChatGPT / Codex runtime — Personal GRC Agent

## Setup

```bash
source .venv/bin/activate
spa init --runtime chatgpt
```

Codex CLI reads **`AGENTS.md`** at the repo root natively. ChatGPT Desktop users register the governed MCP server from the snippet in this doc (also written by init).

### ChatGPT Desktop MCP (stdio)

```json
{
  "mcpServers": {
    "pga-governed": {
      "type": "stdio",
      "command": ".venv/bin/spa",
      "args": ["mcp", "serve"]
    }
  }
}
```

Run from the repo root after `./bootstrap.sh`.

## Skills

Use `spa run-skill <name> --input <path>` or `pga_run_skill` on the governed MCP server. Codex does not auto-load `skills/` like Claude Code — skill contracts inform LLM mode when `LLM_API_KEY` is set.

## Governance

Same ToolGuard + audit spine as all runtimes. No live vendor writes in MVP.

## E2E

```bash
./scripts/e2e/run-chatgpt.sh
```

## Limitations

- ChatGPT Desktop MCP registration is manual (copy from `docs/runtimes/chatgpt.md` after init).
- E2E degrades to MCP stdio when `codex` CLI is absent (`SKIPPED-RUNTIME-NATIVE`).
