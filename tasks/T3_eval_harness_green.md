# T3 — Make the eval harness pass green on all skills

## Context
Every skill folder has a `skill.md` and `output.schema.json`, and most have a
`verifiers/` dir. The eval harness must score each skill's draft output against a
golden output and fail CI on drift.

## Goal
A single command runs all skill evals, scores draft vs golden, and exits
non-zero on any miss.

## Files touched
- `evals/run_evals.py` — load fixtures, run each skill, compare to golden, print
  one PASS/FAIL line per skill, exit non-zero on any failure. Set
  `SPA_DATA_DIR`/`SPA_AUDIT_DIR` to `/tmp/spa_d` and `/tmp/spa_a` when unset
  so audit/data writes stay outside the repo tree.
- `evals/fixtures/` — ensure ≥1 sanitized input per skill
  (meeting-synth, ticket-draft, policy-redline, csf-crosswalk, evidence-pack,
  daily-brief).
- `evals/golden-outputs/` — ensure a matching golden file per fixture.
- `evals/rubrics/` — per-skill success rubric used for scoring.
- `skills/evidence-pack/` — add `output.schema.json` + `verifiers/` (currently
  missing; only `skill.md` exists).

## Acceptance criteria
- `SPA_DATA_DIR=/tmp/spa_d SPA_AUDIT_DIR=/tmp/spa_a python evals/run_evals.py`
  exits 0 (isolated paths avoid writing into the repo tree / T1 write-block).
- Output shows exactly one PASS line for each of the 6 skills.
- Deliberately corrupting one golden file makes the run exit non-zero.
- Running evals creates no files under `governance/` or `workspace/`.

## Do NOT
- Do not weaken scoring to force a pass. Fix the skill or the fixture instead.
