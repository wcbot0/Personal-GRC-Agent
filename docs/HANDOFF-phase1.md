# Phase 1 Handoff — PGA Harness Core

**Status:** Handoff-ready for Cursor agent
**Branch:** `feat/phase1-harness-core` (create from `main`; do not commit to `main`)
**Prime directive:** Keep `pytest tests/`, `make eval`, `make lint`, and `make redteam` green after every milestone. Do not begin a milestone until the prior one passes. Follow `AGENTS.md` conventions and the A0–A5 autonomy policy — this work is all A1 (local drafts on a feature branch).

## Context

PGA's governance spine (ToolGuard, CPO queue, hash-chained audit, verifiers) is complete and tested (123 tests, 6/6 evals). Phase 1 closes the three gaps that block PGA from being a true multi-runtime agent harness:

1. Chat agents bypass governance (raw MCP filesystem mounts).
2. Skill logic is deterministic stubs (no LLM calls).
3. Repo hygiene drift.

---

## Milestone 1.1 — Hygiene sweep (small, do first)

- Move `SPA_MVP` → `docs/SPA_MVP.md` (create `docs/`). Update any references.
- Delete `brain/policies/` (identical legacy duplicate of `brain/03-policies/`). Grep for references first; update if any.
- Reconcile `brain/00-meta/README.md` with reality: create `brain/04-standards/`, `brain/05-procedures/`, `brain/06-risks/`, `brain/07-evidence/`, `brain/08-decisions/` each with a one-paragraph README, or note `evidence/` as the active convention.
- Rename `Security's Personal Agent.code-workspace` → `pga.code-workspace` (apostrophe breaks tooling).
- README: fix "40+ tests" → actual count; no other README changes.

**Accept:** all suites green; no dangling references (grep `SPA_MVP`, `brain/policies`).

## Milestone 1.2 — `spa mcp serve` (governed MCP server)

New module `spa/mcp_server.py` + CLI command `spa mcp serve` (stdio transport).

- Use the official `mcp` Python SDK (FastMCP). Add to `pyproject.toml`.
- Expose tools, each delegating to the EXISTING guarded functions (never reimplement logic):
  - `pga_ingest(path)` → `spa.ingest`
  - `pga_run_skill(skill, input_path, output_dir?)` → `spa.skills.runner.run_skill`
  - `pga_proposals_list()` / `pga_proposals_show(id)` → approval queue reads
  - `pga_proposals_approve(id)` / `pga_proposals_reject(id, reason)` → **classify A3 via ToolGuard**; these are the human-gate — include a `confirm: true` arg requirement and document that MCP clients must surface this to the human
  - `pga_audit_verify(from?, to?)`
  - `pga_memory_search(query, k=5)` → episodic FTS + semantic search (offline fallback OK)
- Every tool call must route through `ToolGuard` classification and emit audit events, same as the CLI path.
- Add `mcp/pga-governed.json` (enabled) registering the server; update `scripts/setup-hermes.sh` to register it and demote the raw filesystem mount to `brain/` read-only browsing.
- Tests: `tests/test_mcp_server.py` — tool registry matches spec, ingest/run_skill produce audited artifacts, approve without `confirm` fails, unknown tool name → A5 blocked.
- Docs: short section in `AGENTS.md` and `README.md` ("Connect any MCP client").

**Accept:** `spa mcp serve` starts; a scripted MCP client round-trip (ingest fixture → run meeting-synth → list proposals) passes in a test; audit chain verifies after.

## Milestone 1.3 — LLM-backed skill engine

New `spa/llm/client.py`: provider-agnostic chat-completion client.

- Providers via env (`LLM_PROVIDER`: `openai` | `anthropic` | `ollama`; plus `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`). Use `httpx` directly (no heavy SDKs).
- Never log prompts/keys; redact content through existing redaction before sending; audit-log model+latency+token counts only.
- Upgrade `meeting-synth` and `csf-crosswalk` to LLM mode: build prompt from skill contract (`skills/<name>/skill.md`) + input + relevant brain snippets (semantic search, top-3); parse strict JSON to the existing output schema.
- Verifier loop: generate → schema+rubric verify → on fail, retry once with verifier feedback → on second fail, existing CPO+block behavior.
- **Deterministic fallback preserved:** if no `LLM_API_KEY` or `SPA_NO_LLM=1`, use current heuristic implementations. CI runs deterministic mode — golden evals must stay green unchanged.
- Tests: mock httpx; cover provider selection, JSON parse failure → retry → CPO, fallback mode.

**Accept:** all suites green in deterministic mode; with a mocked LLM, both skills produce schema-valid output and audit events.

## Milestone 1.4 — Wrap-up

- Update `CHANGELOG` section in README or add `CHANGELOG.md`.
- Open a draft PR from `feat/phase1-harness-core` with a summary table of milestones, test counts, and any deviations. Do NOT merge (A4 — human approval).
