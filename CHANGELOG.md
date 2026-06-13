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

### Review fixes (Phase 2 Milestone 2.0)

- Removed writable `pga-filesystem` Hermes mount; governed MCP (`pga-governed`) is the only registered server
- Pinned `SPA_NO_LLM=1` in CI workflow jobs running pytest, eval, and redteam
- `LLM_PROVIDER=ollama` enables LLM without `LLM_API_KEY` (still disabled by `SPA_NO_LLM=1`)
- Documented `_execute_human_gate` ToolGuard bypass rationale in `spa/mcp_server.py`
