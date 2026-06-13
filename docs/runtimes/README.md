# Runtime setup

PGA runs the same skills, Security Brain, and governance on every runtime. Pick your AI assistant and run one-time init:

```bash
source .venv/bin/activate
spa init --runtime <name>
```

| Runtime | Guide | Best for |
|---------|-------|----------|
| **Cursor** | [cursor.md](cursor.md) | IDE-integrated GRC drafting with workspace rules |
| **Claude Code** | [claude.md](claude.md) | Native skill discovery + governed MCP |
| **Hermes** | [hermes.md](hermes.md) | Conversational Security Brain access |
| **ChatGPT / Codex** | [chatgpt.md](chatgpt.md) | Codex CLI or ChatGPT Desktop MCP |
| **OpenClaw** | [openclaw.md](openclaw.md) | OpenClaw Gateway with skills roots |

All runtimes connect to **`pga-governed`** MCP (`spa mcp serve`) for ingest, skills, proposals, audit verify, and memory search.

**Before setup:** complete [Getting started](../getting-started.md) (bootstrap + `make selftest`).

**After setup:** verify with `spa init --runtime <name> --check`, `make selftest`, and `spa audit verify`.

Agent navigation (paths, skill routing, CPO rules): [AGENTS.md](../../AGENTS.md)
