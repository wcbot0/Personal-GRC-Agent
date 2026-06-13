# Phase 3 Handoff — Useful Depth

**Status:** Handoff-ready for Cursor agent
**Branch:** `feat/phase3-useful-depth` (create from `main` at or after merge commit `20560b9`; do not commit to `main`)
**Prime directive:** Keep `pytest tests/`, `make eval`, `make lint`, `make redteam`, and `spa audit verify` green after every milestone. Do not begin a milestone until the prior one passes. Follow `AGENTS.md` conventions and the A0–A5 autonomy policy — all build work is A1 (local drafts on a feature branch). Conventional commits; one milestone per commit.

## Operating guidance (driving this with Cursor interactively)

Headless `cursor-agent -p` hangs on this repo's multi-turn coding runs (diagnosed June 13: explores, then the non-interactive loop freezes and never resumes — independent of scope or prompt). Run Cursor in its **normal interactive TUI** instead and build **one milestone per session**:

1. Point Cursor at this doc (or paste the relevant milestone) and have it implement a single milestone end to end.
2. Keep each milestone in its own conventional commit (`feat(phase3): milestone 3.N — …`).
3. After each milestone, run the full gate yourself (or ask the orchestrator to): `pytest tests/`, `make eval`, `make lint`, `make redteam`, `spa audit verify` — all green before starting the next.
4. The orchestrator (Perplexity) will review each commit for governance, run the gate, and handle reconcile + merge to `main` (fetch origin first — `main` may have advanced via parallel PRs; resolve duplicate-fix conflicts by taking the canonical `origin/main` side and hand-merging docs).
5. Watch for the macOS case-insensitivity git trap on any file renames (use a two-step `git mv` through a temp name).

## Context

Phases 1–2 delivered the governed MCP server, the LLM-backed skill engine, and five-runtime coverage (SKILL.md spec, `spa init --runtime`, per-runtime E2E). Phase 3 turns the harness from "governed and portable" into "useful day to day": real external draft surfaces, a cloud findings loop, a questionnaire skill, installable framework brain packs, and reliability metrics.

**Governance is non-negotiable.** Every new external write path must route through ToolGuard and the CPO queue. Connectors ship **write-disabled by default** (`connectors.*.live_write_enabled: false` in `agent/autonomy-policy.yaml`); live writes are opt-in, gated, and never self-approvable. Nothing in this phase may create a path that bypasses redaction-at-write or the hash-chained audit.

---

## Milestone 3.1 — Linear live A2 writes behind CPO

First real external draft surface. Enable creating **AI-Proposed** Linear issues from existing ticket proposals, gated at A2 (`create_ai_proposed_ticket` → notify) with the live write itself behind an explicit CPO + connector flag.

- Add a Linear write client alongside the existing read client; respect `connectors.ticket.live_write_enabled` (default false) — when false, calls produce a local draft + CPO only, never a network write.
- Flow: ticket proposal → CPO (A2 notify) → on approval, create issue in Linear with an `AI-Proposed` label and a provenance comment (skill, input sha256, run_id, CPO id). All emitted as audit events.
- `confirm: true` semantics for the approval surface, consistent with the MCP human-gate.
- Tests: mock the Linear API; cover write-disabled (draft+CPO only, zero network), write-enabled+approved (one issue, provenance comment, audit events), write-enabled+unapproved (blocked). No live calls in CI.

**Accept:** all suites green; with the flag off, behavior is identical to today (drafts only); with the flag on and a mocked client, an approved proposal creates exactly one labeled issue with provenance and full audit trail.

## Milestone 3.2 — Cloud findings pipeline

Scheduled read-only AWS/GCP checks → findings → ticket proposals → evidence index.

- Drive checks from the existing `cloud-checks.yaml` via the existing read-only AWS/GCP clients (all A0 reads). No write/remediation calls — remediation surfaces only as ticket proposals (A2).
- `spa cloud scan` (one-shot) producing `findings/<provider>-<timestamp>.json`; each finding maps to a control tag and an optional ticket proposal.
- Evidence index: append findings to an evidence index keyed by control/period for audit-season reuse.
- Provide a scheduler hook (cron-friendly entrypoint) but do not register a live schedule — document it.
- Tests: fixture cloud responses (no live cloud calls); findings JSON shape, control mapping, proposal creation, evidence index append, audit events.

**Accept:** all suites green; `spa cloud scan` on fixtures yields findings JSON + proposals + evidence index entries, all audited; zero write calls to cloud providers.

## Milestone 3.3 — Questionnaire skill (CAIQ/SIG)

New skill `questionnaire` (SKILL.md + schema + rubric + golden fixture) that ingests a security questionnaire and drafts answers grounded in `brain/`.

- Input: CAIQ/SIG-style CSV/XLSX/markdown question list. Output schema: per-question answer + brain citations (policy/control refs) + confidence + `needs_human` flag.
- LLM mode via the Phase 1 engine with deterministic fallback; answers must cite brain sources, and low-confidence/unsupported answers set `needs_human` (never fabricate a citation).
- Verifier: every answered question has at least one citation or `needs_human=true`; schema + rubric gates as with other skills.
- Register in `SKILL_MODULES`, the runner, and `spa run-skill`; add golden fixture + eval lane.

**Accept:** all suites green incl. the new golden eval; deterministic mode stable; mocked-LLM mode produces schema-valid, cited answers and flags unsupported ones.

## Milestone 3.4 — Brain packs v1 (ISO 42001 + NIST AI RMF)

Installable, versioned framework content packs.

- `spa brain add <pack>` / `spa brain list` — install a pack into `brain/04-standards/<pack>/` (or the active convention) with a manifest (`pack.yaml`: name, version, source, license note) and re-index into semantic memory.
- Ship two packs: `iso-42001` and `nist-ai-rmf` (concise, citable overviews of controls/functions; strongest thematic fit for an AI-governance harness). Content must cite authoritative sources in each doc.
- Idempotent install; `--check` reports installed packs + versions.
- Tests: install into a tmp brain dir, manifest parse, semantic re-index hook called, idempotency, list/check output.

**Accept:** all suites green; both packs install idempotently, are discoverable via semantic search, and carry source citations + version manifests.

## Milestone 3.5 — Reliability metrics (M1/M2) in daily brief

Instrument and surface the spec's reliability metrics (only M3 verifier pass-rate exists today).

- **M1 first-pass acceptance:** record edit distance between AI draft and the approved/edited CPO outcome; report acceptance rate.
- **M2 time-to-detect:** time from finding/risk creation to CPO creation.
- Persist alongside the existing `governance/eval-history/`; render M1/M2 (with M3) in the `daily-brief` skill output.
- Tests: metric computation from fixture CPO/audit data; daily-brief renders all three.

**Accept:** all suites green; daily brief shows M1/M2/M3; metrics computed from audit/CPO history, not hardcoded.

## Milestone 3.6 — Wrap-up

- Update `CHANGELOG.md` (Phase 3 section); refresh README where new commands (`spa cloud scan`, `spa brain add`) and the questionnaire skill belong.
- Open a draft PR from `feat/phase3-useful-depth` with a milestone summary table, test counts, and any deviations. Do NOT merge (orchestrator reviews and makes the merge call).

## Out of scope (Phase 4 — community release)

PyPI release as `pga`, skill SDK + `spa skill new` promotion, conformance badge, community skill registry, one-line `uvx`/`pipx` install, encrypted memory sync.
