# T5 — Prove the A3+ gate blocks without an approved CPO

## Context
The action-risk model in `agent/autonomy-policy.yaml` defines A0–A5. The tool
guard must enforce it: A3+ actions cannot execute without an approved Change
Proposal Object (CPO).

## Goal
Any attempt at an A3+ action with no approved CPO is refused, emits a CPO, and is
logged — never silently executed.

## Files touched
- `spa/tools/guard.py` — classify each action, block A3+ without an approved CPO,
  emit a CPO into the queue, write an audit event.
- `spa/governance/approval_queue.py` — CPO create/lookup/approve state machine.
- `agent/autonomy-policy.yaml` — confirm gated actions: `assign_human`,
  `raise_priority` above High, terminal ticket states, `merge_pr`,
  `publish_policy`, `grc_write` (post-MVP), and BLOCKED A5 actions.

## Acceptance criteria
- selftest `test_tool_guard_blocks_a3` passes.
- selftest `test_cpo_lifecycle` passes.
- A scripted `assign_human` attempt with no CPO returns refused + creates a
  `pending_approval` CPO + writes an audit event.
- An A5 action (e.g., `secret_rotation`) is blocked outright (not gated).

## Do NOT
- Do not allow an "auto-approve" path for A3+ in MVP.
