# pga-init-managed

# Hermes runtime — Personal GRC Agent

Use [Hermes Agent](https://hermes-agent.nousresearch.com/) for conversational access to your Security Brain via governed MCP.

**Prerequisites:** [Getting started](../getting-started.md) — bootstrap complete, `spa` on your PATH.

## Setup

Option A — during bootstrap (interactive):

```bash
./bootstrap.sh
```

Option B — wire Hermes after bootstrap:

```bash
./scripts/setup-hermes.sh
```

Option C — via runtime init:

```bash
spa init --runtime hermes
```

This registers **`pga-governed`** in `~/.hermes/config.yaml` (ToolGuard + audit). Legacy writable filesystem mounts are removed on re-run.

Configure your model and API keys in Hermes (`hermes model`). Keys live in `~/.hermes/.env`, not PGA's `.env`.

Start chat from the **repo root** so `AGENTS.md` loads:

```bash
hermes chat
```

## Using PGA in Hermes

Prefer **`pga-governed`** MCP for ingest, skills, proposals, and audit. Browse `brain/` in your editor or use `pga_memory_search` from chat.

Example session flow:

1. Drop notes in `inbox/`
2. Ask Hermes to ingest via `pga_ingest`
3. Review ticket proposals under `workspace/proposals/tickets/`
4. Approve CPOs only when you explicitly confirm

## Governance

Governed MCP is preferred over chat file writes for anything that must pass verifiers. Approve and reject require human confirmation in the client.

## Verify setup

```bash
hermes mcp test pga-governed    # test MCP connection
spa audit verify
make selftest
```

| Symptom | Fix |
|---------|-----|
| `hermes: command not found` | Reload shell or reinstall Hermes |
| MCP won't connect | Run `./bootstrap.sh`; confirm `spa` is on PATH |
| Chat ignores PGA rules | Start `hermes chat` from repo root |
| API key errors | Configure keys in `~/.hermes/.env` |

## Limitations

- Hermes must be installed separately (`hermes setup` first).
- `setup-hermes.sh` modifies `~/.hermes/config.yaml` (user-level, not committed).

## See also

- [Getting started](../getting-started.md)
- [AGENTS.md](../../AGENTS.md)
