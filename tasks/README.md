# SPA MVP — Cursor Task Queue

Feed these to a Cursor agent **one at a time, in order**. Do not start a task
until the previous task's acceptance criteria pass. Each file names the exact
files to touch and a binary acceptance check.

## Order & dependencies

| # | Task | Phase | Blocks |
|---|------|-------|--------|
| T1 | Fix environment write-block | A: Unblock | ALL |
| T2 | Configurable + test-isolated state paths | A: Unblock | T3–T9 |
| T3 | Eval harness green on all skills | B: Skills | T4, T8 |
| T4 | End-to-end meeting-synth (file-only) | B: Skills | — |
| T5 | A3+ gate blocks without approved CPO | C: Governance | T6 |
| T6 | Approval queue CLI round-trip | C: Governance | — |
| T7 | Redaction-at-write coverage | D: Hardening | T8 |
| T8 | CI green in GitHub Actions | D: Hardening | — |
| T9 | Connector contract test (adapters off) | D: Hardening | — |

## Critical path
T1 → T2 → (T3 → T4) and (T5 → T6) in parallel → T7 → T8 → T9

## MVP Definition of Done (from the build plan)
- Fresh clone + bootstrap → running agent < 30 min.
- All 6 skills pass golden-fixture evals in CI.
- All A3+ actions blocked without an approved CPO; audit log reconstructs every action.
- No secrets in git; secret scan + redaction tests pass.
- GRC + ticket adapters present but disabled; file-only mode fully functional.

## Note on T1
T1 is an **environment** fix (macOS sandbox/TCC), not code. Every other task's
test run depends on it because audit logs and the SQLite/Qdrant data must be
writable.
