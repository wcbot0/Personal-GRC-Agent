# Changelog

All notable changes to Personal GRC Agent (PGA) are documented here.

## [Unreleased] — Phase 1 Harness Core

### Milestone 1.1 — Hygiene sweep

- Moved `SPA_MVP` → `docs/SPA_MVP.md`; updated legacy `brain/policies/` references to `brain/03-policies/`
- Removed duplicate `brain/policies/` tree
- Added `brain/04-standards/` through `brain/08-decisions/` README stubs; reconciled `brain/00-meta/README.md` with active `brain/evidence/` convention
- Renamed `Security's Personal Agent.code-workspace` → `pga.code-workspace`
- README: corrected test count

### Milestone 1.2 — Governed MCP server

- Added `spa mcp serve` (FastMCP stdio) in `spa/mcp_server.py`
- Exposed ToolGuard-wrapped tools: ingest, run-skill, proposals, audit verify, memory search
- Approve/reject require `confirm: true` (A3 human gate)
- Added `mcp/pga-governed.json`; updated `scripts/setup-hermes.sh` (governed server + read-only brain filesystem)
- Tests: `tests/test_mcp_server.py` (registry, audit round-trip, stdio client)

### Milestone 1.3 — LLM-backed skill engine

- Added `spa/llm/client.py` (OpenAI, Anthropic, Ollama via httpx)
- Upgraded `meeting-synth` and `csf-crosswalk` with LLM prompts + brain semantic snippets
- Verifier-feedback retry loop; deterministic heuristic fallback when `LLM_API_KEY` unset or `SPA_NO_LLM=1`
- Tests: `tests/test_llm.py` (mocked provider, fallback, retry → CPO)

### Quality gates (branch)

| Suite | Result |
|-------|--------|
| `pytest tests/` | 136 passed |
| `make eval` | 6/6 skills |
| `make lint` | policy-lint + secret-scan OK |
| `make redteam` | 30 cases OK |

### Deviations

- Hermes filesystem MCP demoted to `brain/` read-only only (inbox/drafts no longer mounted) — governed MCP is the preferred write path
- LLM env supports both `LLM_BASE_URL` and existing `LLM_API_BASE` alias

### Review fixes (pre-merge)

- **Removed `pga-filesystem` mount** — `@modelcontextprotocol/server-filesystem` exposes write tools; setup script now registers `pga-governed` only and idempotently drops legacy `pga-filesystem` from `~/.hermes/config.yaml`
- **CI deterministic mode** — `SPA_NO_LLM=1` pinned in skill-tests and redteam GitHub Actions jobs
- **Ollama without API key** — `llm_enabled()` returns true for `LLM_PROVIDER=ollama` with no `LLM_API_KEY`; OpenAI/Anthropic still require a key
- **Human-gate comment** — documented ToolGuard bypass in `_execute_human_gate` (CPO-to-approve-a-CPO circularity; `confirm=true` is client-asserted)

## [Unreleased] — Phase 2 Five-Runtime Coverage

### Milestone 2.0 — Phase 1 review fixes

- The four review fixes above; merged to main independently via PR #16 and reconciled into this branch

### Milestone 2.1 — SKILL.md spec migration

- Renamed `skills/<name>/skill.md` -> `SKILL.md` with YAML frontmatter (8 skills); real git rename verified on case-insensitive filesystems
- Updated skill engine, scaffold script, docs; added `tests/test_skill_spec.py`
- Pinned `SPA_NO_LLM=1` in `make eval`

### Milestone 2.2 — `spa init --runtime`

- New CLI: `spa init --runtime <cursor|claude|chatgpt|hermes|openclaw>`
- Idempotent glue generation with `--dry-run`, `--check`, `--force`
- Tests: `tests/test_runtime_init.py` (14 cases)

### Milestone 2.3 — Quickstart matrix + E2E

- README five-runtime quickstart table
- `scripts/e2e/run-<runtime>.sh` + shared `mcp_scenario.py`
- Per-runtime docs under `docs/runtimes/`

### Quality gates (branch)

| Suite | Result |
|-------|--------|
| `pytest tests/` | 166 passed |
| `make eval` | 8/8 skills |
| `make lint` | policy-lint + secret-scan OK |
| `make redteam` | 30 cases OK |
| `spa audit verify` | valid |

### Deviations

- Hermes init invokes `setup-hermes.sh` (requires Hermes installed locally)
- E2E scripts degrade to MCP stdio when runtime binary absent (`SKIPPED-RUNTIME-NATIVE`)
- OpenClaw config uses `.openclaw/openclaw.json` (workspace-local, not global `~/.openclaw/`)
