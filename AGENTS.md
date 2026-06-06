# Personal GRC Agent — Hermes workspace rules

You are operating inside the **Personal GRC Agent (PGA)** repository. Read and follow `agent/charter.md` and `agent/autonomy-policy.yaml` for persona and risk gates.

## Draft-by-default

- You may **read** `brain/`, `inbox/`, and `workspace/` freely.
- Produce **drafts only** under `workspace/drafts/`, `workspace/proposals/`, and `brain/03-policies/proposals/`.
- Do **not** assign tickets to humans, publish policies, merge PRs, or write to external GRC/ticket systems without an approved Change Proposal Object (CPO).
- In MVP, ticket and GRC connectors are stubs — write AI-Proposed ticket JSON files instead.

## Governed operations (use the `spa` CLI)

For verifier-gated skills, hash-chained audit logs, redaction-at-write, and ToolGuard enforcement, run commands in the repo's virtualenv instead of writing files directly:

```bash
source .venv/bin/activate
spa ingest inbox/my-notes.md
spa run-skill meeting-synth --input inbox/my-notes.md
spa run-skill ticket-draft --input path/to/input.md
spa proposals list
```

Skills live in `skills/` (meeting-synth, ticket-draft, policy-redline, csf-crosswalk, daily-brief, evidence-pack).

## Key paths

| Path | Purpose |
|------|---------|
| `brain/` | Security Brain — frameworks, policies, controls, evidence |
| `inbox/` | Drop raw notes here, then `spa ingest` |
| `workspace/drafts/` | Skill output and ticket proposals |
| `governance/approval-queue/` | Pending CPOs awaiting human approval |
| `governance/audit-logs/` | Hash-chained JSONL audit trail |

## Memory

Semantic search (Qdrant) and episodic memory (SQLite) are populated by `./bootstrap.sh` and `make seed`. Re-seed after adding brain content: `make seed`.
