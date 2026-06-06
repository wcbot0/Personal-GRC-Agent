# T7 — Redaction-at-write coverage

## Context
Nothing should be persisted to memory (SQLite or Qdrant) before deterministic
redaction of secrets/PII. The rules live in `governance/redaction-rules.yaml`.

## Goal
Every persistence path runs redaction first; a planted secret never reaches disk.

## Files touched
- `spa/memory/redaction.py` — apply rules to content before any persist call.
- `governance/redaction-rules.yaml` — patterns: API keys, tokens, AWS keys,
  emails (configurable), private-key blocks, plus a denylist.
- `spa/memory/episodic.py` / `spa/memory/semantic.py` — ensure they call
  redaction on the write path (not just at read).
- `tests/test_memory.py` — `test_ingest_redacts_before_persist`.

## Acceptance criteria
- A fixture containing a fake secret (e.g., `AKIA...`, a bearer token) is redacted
  before SQLite AND Qdrant persistence.
- `test_ingest_redacts_before_persist` passes.
- The raw secret string is absent from the on-disk SQLite DB and vector payloads.

## Do NOT
- Do not redact only at display time; redaction must happen at write time.
