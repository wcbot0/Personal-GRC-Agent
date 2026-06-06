# T4 — End-to-end meeting-synth → ticket + policy draft (file-only mode)

## Context
This is the core MVP workflow: drop a transcript in `inbox/`, the agent
synthesizes it and produces draft artifacts — with NO live vendor writes
(`TICKET_PROVIDER=none`, `GRC_PROVIDER=none`).

## Goal
`make ingest FILE=evals/fixtures/meeting_sample.md` produces a complete set of
draft artifacts and audit entries.

## Files touched
- `spa/ingest.py` — wire file ingest → meeting-synth → downstream skills.
- `spa/skills/meeting_synth.py` — emit decisions, risks, action items, control tags.
- `spa/skills/ticket_draft.py` — emit ticket-proposal file(s): unassigned,
  suggested owner + rationale in body, control tags.
- `spa/skills/policy_redline.py` — if a policy change is implied, write a redline
  to `brain/03-policies/proposals/` on an `agent/` branch + a Draft-PR-body file.
- `connectors/tickets/none/provider.py` — write tickets as files under
  `workspace/proposals/`.

## Acceptance criteria (all must appear from one ingest run)
- Ticket-proposal file(s) in `workspace/proposals/` (unassigned + suggested owner).
- Control tags present on outputs (SOC2 CC + CSF).
- For any policy change: redline file in `brain/03-policies/proposals/` + Draft-PR-body file.
- One audit event per discrete action in the JSONL log.
- All skill verifiers pass on the run.

## Do NOT
- Do not assign tickets to any human.
- Do not open/merge real PRs or call any vendor API.
