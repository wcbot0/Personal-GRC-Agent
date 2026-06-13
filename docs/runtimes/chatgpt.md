# pga-init-managed

# ChatGPT / Codex runtime — Personal GRC Agent

Use OpenAI Codex CLI or ChatGPT Desktop with PGA's governed MCP server.

**Prerequisites:** [Getting started](../getting-started.md) — bootstrap complete, `spa` on your PATH.

## Setup

```bash
source .venv/bin/activate
spa init --runtime chatgpt
```

**Codex CLI** reads **`AGENTS.md`** at the repo root natively. Work from the repo root after `./bootstrap.sh`.

**ChatGPT Desktop** users register the governed MCP server manually. Use this stdio configuration (also written by init):

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

Adjust the `command` path if your virtualenv lives elsewhere. The server must start with the repo as its working directory.

## Using PGA with Codex / ChatGPT

Run skills via terminal or MCP:

```bash
spa run-skill meeting-synth --input inbox/my-notes.md
spa ingest inbox/my-notes.md
```

Or call `pga_run_skill` and `pga_ingest` on the governed MCP server.

Codex does not auto-load `skills/` like Claude Code — skill contracts inform LLM mode when `LLM_API_KEY` is set in `.env`.

## Governance

Same ToolGuard and audit spine as all runtimes. No live vendor writes by default (`TICKET_PROVIDER=none`). Approve and reject require explicit confirmation.

## Verify setup

```bash
make selftest
spa audit verify
spa proposals list
```

Test MCP manually: run `spa mcp serve` from the repo root and confirm your client connects.

## Limitations

- ChatGPT Desktop MCP registration is manual — copy the JSON snippet above into your client settings.
- Codex and ChatGPT do not load `AGENTS.md` workspace rules the same way Cursor does; prefer explicit `spa` commands or MCP tools for governed work.

## See also

- [Getting started](../getting-started.md)
- [AGENTS.md](../../AGENTS.md)
