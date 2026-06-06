# T6 — Approval queue CLI round-trip

## Context
The human gate needs an ergonomic CLI so you can review and approve/reject the
agent's proposed actions.

## Goal
Full CPO lifecycle from the command line, with every transition audited.

## Files touched
- `spa/cli.py` — implement subcommands.
- `spa/governance/approval_queue.py` — back the CLI operations.

## Commands to implement
- `spa proposals list` — list pending CPOs (id, type, risk, summary).
- `spa proposals show <id>` — full CPO + the diff/preview it would execute.
- `spa proposals approve <id>` — approve + execute the gated action.
- `spa proposals reject <id> --reason "..."` — reject (reason REQUIRED).
- `spa proposals approve --batch --type <type> --max-risk A3` — batch approve.

## Acceptance criteria
- Create CPO → `list` shows it → `show` prints it → `approve` executes → audit
  log records each transition.
- `reject` with no `--reason` errors out.
- Batch approve respects both `--type` and `--max-risk` filters.

## Do NOT
- Do not let approve/reject run without writing an audit event.
