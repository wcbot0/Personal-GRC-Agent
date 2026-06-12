# CLAUDE.md — Personal GRC Agent

Guidance for Claude Code sessions in this repo. **Canonical agent navigation lives in `AGENTS.md`** — read it first for paths, ingest routing, skills, and storage conventions.

Also read at session start:
- `agent/charter.md` — persona and draft surfaces
- `agent/autonomy-policy.yaml` — action-risk gates (A0–A5)

---

## What this repo is

**Personal GRC Agent (PGA)** is a local-first, draft-by-default GRC copilot. The Python CLI is **`spa`**. It produces verified drafts (meeting synth, tickets, policy redlines, evidence indexes) without auto-publishing to external systems.

---

## Quick commands

```bash
source .venv/bin/activate
./bootstrap.sh                    # first-time setup
make seed                         # re-index brain/ → Qdrant after brain edits
make selftest                     # health checks
pytest tests/ -v                  # unit/integration tests

spa ingest inbox/<file>.md        # ingest + auto-pipeline (meeting detect)
spa run-skill <skill> --input <path> [--output-dir <dir>]
spa proposals list                # pending CPOs
spa audit verify                  # hash chain integrity
```

Skills: `meeting-synth`, `ticket-draft`, `policy-redline`, `csf-crosswalk`, `daily-brief`, `evidence-pack`, `risk-analyst`

---

## Code layout

| Path | Purpose |
|------|---------|
| `spa/` | CLI, skill runner, memory, governance, audit chain |
| `connectors/` | Ticket/GRC/cloud/notes interfaces (MVP stubs) |
| `skills/` | Skill contracts, output schemas, verifiers |
| `brain/` | Security Brain — frameworks, policies, controls, evidence |
| `inbox/` | Raw inputs → `spa ingest` |
| `workspace/` | Drafts and proposals (see `AGENTS.md` for path patterns) |
| `governance/` | Audit logs, approval queue, redaction rules |
| `tests/` | Enforcement, audit chain, ingest e2e |
| `evals/` | Golden fixtures and skill eval harness |

Canonical path resolution: `spa/paths.py`

---

## Non-negotiable rules (summary)

- **Draft-by-default.** Read `brain/`, `inbox/`, `workspace/` freely. Write drafts only in allowed surfaces (`AGENTS.md` § Storage paths).
- **Use `spa` for governed work.** Ingest, skills, verifiers, and audit trail — do not hand-craft skill JSON or ticket files when audit matters.
- **MVP:** tickets stay `status: ai_proposed`, `assignee: unassigned`. No live vendor writes.
- **A3+ requires CPO:** assign humans, publish policies, merge PRs, GRC writes — all need approved Change Proposal Objects.
- **A5 blocked:** delete audit logs or evidence, write directly to `governance/audit-logs/`.
- **After brain edits:** `make seed`. Never commit `.env` or secrets.

Full routing, artifact naming, and workflows: **`AGENTS.md`**.
