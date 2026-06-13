# Phase 2 Handoff — Five-Runtime Coverage

**Status:** Handoff-ready for Cursor agent
**Branch:** `feat/phase2-runtime-coverage` (create from `main` at or after merge commit `93449cb`, PR #15; do not commit to `main`)
**Prime directive:** Keep `pytest tests/`, `make eval`, `make lint`, `make redteam`, and `spa audit verify` green after every milestone. Do not begin a milestone until the prior one passes. Follow `AGENTS.md` conventions and the A0–A5 autonomy policy — this work is all A1 (local drafts on a feature branch). Conventional commits; one milestone per commit.

## Context

Phase 1 delivered the governed MCP server (`spa mcp serve`), the LLM-backed skill engine with deterministic fallback, and the hygiene sweep. Phase 2 makes the harness genuinely runtime-agnostic: the same brain, skills, and governance regardless of whether the human drives Cursor, Claude Code, ChatGPT (Desktop/Codex), Hermes, or OpenClaw.

Three gaps remain:

1. `skills/*/skill.md` does not follow the SKILL.md spec (no YAML frontmatter, lowercase name), so Claude Code and OpenClaw skill loaders cannot auto-discover skills.
2. There is no per-runtime setup story beyond Hermes (`scripts/setup-hermes.sh`) and the hand-maintained `.cursor/rules`.
3. Nothing proves each runtime works end-to-end against the governed server.

---

## Milestone 2.0 — Phase 1 review fixes (do first)

Implement all four fixes specified in the sibling doc `docs/HANDOFF-phase1-fixes.md`: (1) remove the writable `pga-filesystem` brain mount from `scripts/setup-hermes.sh`, (2) pin `SPA_NO_LLM=1` in CI workflow jobs that run tests/evals/redteam, (3) enable `LLM_PROVIDER=ollama` without an API key, (4) comment the `_execute_human_gate` enforcement exception in `spa/mcp_server.py`. One fix per commit, per that doc's accept criteria. Also `git add` both handoff docs (`HANDOFF-phase1-fixes.md`, `HANDOFF-phase2.md`) in the first commit.

**Accept:** all four accept criteria from `HANDOFF-phase1-fixes.md`; all suites green.

## Milestone 2.1 — SKILL.md spec migration

Rename `skills/<name>/skill.md` → `skills/<name>/SKILL.md` for all 8 skills and add YAML frontmatter:

```yaml
---
name: meeting-synth
description: Synthesize meeting notes into decisions, risks, action items, and proposed tickets. Use when raw meeting notes or transcripts land in the inbox.
---
```

- `description` must state both what the skill does and when to use it (loader discovery hint for Claude Code / OpenClaw).
- Keep `output.schema.json`, rubrics, and golden fixtures exactly where they are (supporting files per the spec).
- Update every reader: `spa/llm/skill_engine.py::_load_skill_contract`, the skill scaffold script (`spa skill new` / `scripts/new-skill.sh`), docs, and any tests that reference `skill.md`. Grep for `skill.md` — zero dangling references.
- Loader-compat tests (`tests/test_skill_spec.py`): every skill dir contains `SKILL.md`; frontmatter parses with required `name` (matching dir name) and `description` (non-empty, contains a when-to-use clause); body content preserved below frontmatter; `_load_skill_contract` returns body + schema unchanged.
- Hygiene rider: pin `SPA_NO_LLM=1` in the CI eval/test lanes (workflows + Makefile eval target) so golden evals stay deterministic even if an `LLM_API_KEY` secret is ever added to CI.

**Accept:** all suites green; frontmatter validates for all 8 skills; no references to lowercase `skill.md` remain; golden evals unchanged.

## Milestone 2.2 — `spa init --runtime <cursor|claude|chatgpt|hermes|openclaw>`

New CLI command generating/validating per-runtime glue. Idempotent (safe to re-run), with `--dry-run` printing planned changes and `--check` exiting nonzero if glue is missing/stale. Never overwrite user-modified files without `--force`.

Per-runtime profiles:

- **cursor:** verify/refresh `.cursor/rules/*.mdc`; ensure repo-root `AGENTS.md` reference; emit MCP registration JSON for Cursor (`.cursor/mcp.json`) pointing at `spa mcp serve`.
- **claude:** ensure `CLAUDE.md` exists (thin shim pointing at `AGENTS.md`); emit `.mcp.json` (project-scope MCP registration for Claude Code) for `pga-governed`; note that `skills/` is auto-discovered via SKILL.md.
- **chatgpt:** Codex CLI reads `AGENTS.md` natively — emit a short `docs/runtimes/chatgpt.md` note; for ChatGPT Desktop, emit the MCP server registration JSON snippet for `pga-governed` (stdio).
- **hermes:** wrap existing `scripts/setup-hermes.sh` behavior (governed server + brain browse); do not duplicate logic — invoke or generate the same config.
- **openclaw:** generate OpenClaw workspace wiring (skills dir registration + MCP registration for `pga-governed`) per OpenClaw workspace conventions.

All generated files are A1 local drafts; `spa init` itself performs no network calls and registers through ToolGuard (`write_local_markdown` / new `runtime_init` mapping → A1).

- Tests (`tests/test_runtime_init.py`): each profile generates expected files in a tmp repo; idempotency (second run = no diff); `--check` detects drift; unknown runtime → error listing valid options.

**Accept:** all suites green; `spa init --runtime X --dry-run` works for all five; generated glue references `spa mcp serve` (never raw filesystem writes).

## Milestone 2.3 — Quickstart matrix + per-runtime E2E scenarios

- README: a five-runtime quickstart matrix (runtime | install | one-line setup via `spa init --runtime` | how skills load | how governance is enforced | E2E script).
- `scripts/e2e/run-<runtime>.sh` — one scripted scenario per runtime: drop `evals/fixtures/meeting_sample.md` into the inbox → governed artifact via `pga_run_skill`/CLI → CPO appears → approve with `confirm=true` → `spa audit verify` passes.
  - Where the runtime binary may be absent (CI), the script degrades to the scripted MCP stdio client (same path as `tests/test_mcp_server.py::test_mcp_stdio_round_trip`) and prints SKIPPED-RUNTIME-NATIVE. Scripts must exit nonzero on governance failures, zero on success/skip.
- `docs/runtimes/<runtime>.md` — one page each: setup, what is generated, known limitations.

**Accept:** all suites green; each script runs clean on the dev Mac; README matrix accurate; audit chain verifies after each scenario.

## Milestone 2.4 — Wrap-up

- Update `CHANGELOG.md` (Phase 2 section: migration, init profiles, E2E matrix).
- Open a draft PR from `feat/phase2-runtime-coverage` with a summary table of milestones, test counts, and any deviations. Do NOT merge (A4 — human approval).

## Out of scope (Phase 3+)

Linear live A2 writes behind CPO, cloud findings pipeline, questionnaire skill, brain packs (ISO 42001, NIST AI RMF), M1/M2 metrics instrumentation, PyPI release as `pga`.
