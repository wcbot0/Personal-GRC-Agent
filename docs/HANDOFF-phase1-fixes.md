# Phase 1 Fix-First Handoff — Pre-Merge Review Findings

**Status:** Handoff-ready for Cursor agent
**Branch:** `feat/phase2-runtime-coverage` (Phase 1 merged as PR #15 before these fixes landed; they are now Milestone 2.0 of `docs/HANDOFF-phase2.md`; do not commit to `main`)
**Prime directive:** Keep `pytest tests/`, `make eval`, `make lint`, `make redteam`, and `spa audit verify` green after every fix. Conventional commits; one fix per commit; push to origin when done so the open PR updates. Follow `AGENTS.md` and the A0–A5 policy — all A1 work.

## Context

Phase 1 passed orchestrator review (146/146 tests, 8/8 evals, lint/redteam/audit green) with four findings. The PR was merged before the fixes landed, so they are applied post-merge as Phase 2 Milestone 2.0.

---

## Fix 1 — Brain mount is not actually read-only (medium)

`scripts/setup-hermes.sh` registers `pga-filesystem` via `@modelcontextprotocol/server-filesystem` over `brain/` with a comment claiming "read-only brain browse". The reference filesystem server exposes `write_file`, `edit_file`, and `move_file` within every allowed directory and has no read-only flag (read-only is only achievable via Docker `ro` bind mounts). Net effect: any Hermes session can write to `brain/` bypassing ToolGuard and redaction-at-write — the exact gap Phase 1 was meant to close.

**Change:** Remove the `pga-filesystem` mount registration entirely. The governed server already covers retrieval (`pga_memory_search`) and `brain/` browsing can happen in the human's editor. Specifically:

- Delete the `servers[fs_mcp_name]` block and `FS_MCP_NAME` plumbing (including its `hermes mcp test` check and the `npx` prerequisite check if nothing else needs Node).
- If a config entry named `pga-filesystem` already exists in `~/.hermes/config.yaml`, the script should remove or disable it (idempotent cleanup).
- Update the closing heredoc text and any README/AGENTS.md mention of the filesystem mount.

**Accept:** grep shows no `pga-filesystem` / `server-filesystem` references outside CHANGELOG history; script remains idempotent and passes `bash -n`.

## Fix 2 — Pin deterministic mode in CI (minor)

CI eval/test lanes are deterministic only because no `LLM_API_KEY` exists in the CI environment. Pin it explicitly: set `SPA_NO_LLM: "1"` in the env of every GitHub Actions job that runs `pytest`, `make eval`, or `make redteam` (`.github/workflows/*`). Do NOT pin it in the Makefile — local LLM-mode runs must stay possible.

**Accept:** every CI job that executes tests/evals/redteam has `SPA_NO_LLM` set; suites still green.

## Fix 3 — Ollama provider requires a dummy API key (minor)

`spa/llm/client.py::llm_enabled()` returns False without `LLM_API_KEY`, but Ollama needs no key, making `LLM_PROVIDER=ollama` unusable without a placeholder. **Change:** treat the LLM as enabled when `LLM_PROVIDER=ollama` even with no key (still disabled by `SPA_NO_LLM=1`). Keep the key requirement for openai/anthropic. Guard against the default-provider case: with no `LLM_PROVIDER` and no key, LLM stays disabled (deterministic fallback unchanged). Update/extend `tests/test_llm.py` (ollama enabled without key; openai still disabled without key) and add a one-line note in the README/CHANGELOG LLM config section.

**Accept:** new tests pass; deterministic-fallback tests unchanged and green.

## Fix 4 — Document the human-gate enforcement exception (comment only)

`spa/mcp_server.py::_execute_human_gate` intentionally bypasses `ToolGuard.check_allowed` (a CPO-to-approve-a-CPO would be circular) and re-implements the A5 block check + audit emission. Add a short comment block explaining the rationale and that this path must stay in sync with `guard.py` policy semantics. Also note in the docstring that `confirm=true` is client-asserted — the audit `human_confirmed` field records the client's claim.

**Accept:** comment present; no behavior change; all suites green.

## Wrap-up

- Append a "Review fixes" subsection to the Phase 1 section of `CHANGELOG.md`.
- Run the full gate (`pytest tests/`, `make eval`, `make lint`, `make redteam`, `spa audit verify`) and include results in the final commit message body.
- These fixes are part of the Phase 2 branch; continue with Milestone 2.1 of `docs/HANDOFF-phase2.md`. Do NOT merge (A4 — human approval).
