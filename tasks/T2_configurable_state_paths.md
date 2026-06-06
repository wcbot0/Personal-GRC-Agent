# T2 — Make state paths configurable + test-isolated

## Context
Audit logs, the SQLite episodic DB, and Qdrant data currently write to hardcoded
in-repo paths. Tests should never touch real state, and runtime paths should be
overridable via env vars.

## Goal
Drive all writable-state locations from env vars (with current defaults) and
isolate every test to a temp dir.

## Files touched
- `spa/paths.py` — resolve base dirs from env: `SPA_DATA_DIR`, `SPA_AUDIT_DIR`
  (fall back to existing `workspace/.data` and `governance/audit-logs`).
- `spa/audit/logger.py` — use the resolved audit dir.
- `spa/memory/episodic.py` — use the resolved data dir for the SQLite file.
- `spa/memory/semantic.py` — use the resolved data dir for Qdrant/local store.
- `conftest.py` (NEW, repo root) — pytest fixture that sets `SPA_DATA_DIR` and
  `SPA_AUDIT_DIR` to a per-test `tmp_path` (autouse).

## Acceptance criteria
- `python -m pytest -q` → **6 passed**.
- `python -m spa.selftest` → **6/6 passed**.
- Running tests creates NO files under `governance/` or `workspace/`.

## Do NOT
- Do not delete the existing default paths; env vars override, defaults remain.
