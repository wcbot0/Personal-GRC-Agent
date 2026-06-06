# T1 — Fix the environment write-block (DO FIRST — blocks all other tasks)

## Context
The repo skeleton is complete, but pytest/selftest/evals fail when writing to
`governance/audit-logs/` and `workspace/.data/`. Ownership and permissions are
correct (`literal:wcbot0:staff`, `rwx`). A direct write test returns
`operation not permitted` — this is a macOS sandbox/TCC restriction on the
project path, NOT a code defect.

## Goal
Make the project location writable by the runtime so the agent can append audit
logs and create the local SQLite/Qdrant data.

## Steps (pick the option that fits your setup)
1. **Preferred:** Move the repo out of a protected/synced location into a plain
   path the terminal can write to, e.g. `~/dev/security-personal-assistant`
   (avoid Desktop/Documents/iCloud-synced folders, which trigger TCC prompts).
2. **Or:** Grant your terminal app AND Cursor *Full Disk Access*
   (System Settings → Privacy & Security → Full Disk Access), then restart both.
3. **Or:** Remove a quarantine attribute if present:
   `xattr -dr com.apple.quarantine .`

## Files touched
- `README.md` — add a short "Local run prerequisites" section documenting the
  chosen fix so collaborators reproduce it.

## Acceptance criteria
- `echo test > governance/audit-logs/_t.tmp` succeeds, then `rm governance/audit-logs/_t.tmp`.
- No `Operation not permitted` errors when running `python -m spa.selftest`.

## Do NOT
- Do not change code logic to "work around" the block (e.g., swallowing write
  errors). This is an environment fix only.
