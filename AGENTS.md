# Personal GRC Agent (PGA) — Agent Navigation Guide

You are operating inside **Personal GRC Agent (PGA)**, a local-first, draft-by-default GRC copilot. The Python CLI is **`spa`**; the product name is PGA. Read this file first, then `agent/charter.md` and `agent/autonomy-policy.yaml` for persona and risk gates.

**Canonical path logic lives in `spa/paths.py`.** When in doubt, match what that module resolves — not informal docs that may lag the code.

---

## Session bootstrap

At the start of every session:

1. Read `agent/charter.md` — persona, draft surfaces, skill expectations.
2. Read `agent/autonomy-policy.yaml` — classify every action A0–A5 before executing.
3. Activate the venv when running governed commands: `source .venv/bin/activate`.
4. Assume **MVP mode**: ticket and GRC connectors are file-only stubs (`TICKET_PROVIDER=none`). No live vendor writes.

---

## Two operating modes

| Mode | Use when | Gets you |
|------|----------|----------|
| **`spa` CLI** (preferred for real work) | Producing auditable artifacts, ingest, skills, CPO workflow | ToolGuard, redaction-at-write, verifier gates, hash-chained audit logs |
| **`spa mcp serve`** (governed MCP) | Chat clients (Hermes, Claude Desktop, Cursor MCP) needing audited tool calls | Same governance spine as CLI — ingest, skills, proposals, audit, memory search |
| **Direct file/MCP writes** (Hermes, Cursor, Claude Code) | Exploration, ad-hoc notes, quick drafts in allowed surfaces | Fast iteration — **no verifier or audit trail** unless you also run `spa` |

**Rule:** Chat agents may read freely and draft in allowed paths. For meeting synthesis, ticket proposals, policy redlines, or anything that must pass verifiers and land in the audit chain, run `spa ingest` or `spa run-skill` — do not hand-write the same artifacts.

---

## What to process (input routing)

Use this decision tree to pick the right entry point:

```
Raw notes / transcript / drop file
  └─► Put in inbox/<descriptive-name>.md
      └─► spa ingest inbox/<file>     ← auto-routes meeting + policy signals

Structured skill input (you know the skill)
  └─► spa run-skill <skill> --input <path>

Security Brain content (frameworks, policies, controls)
  └─► Edit under brain/ (see layout below)
      └─► make seed   ← re-index into semantic memory after substantive adds

Control gap / remediation request
  └─► spa run-skill ticket-draft --input <description.md>

Policy change request
  └─► spa run-skill policy-redline --input <change-request.md>

Vendor questionnaire / artifact crosswalk
  └─► spa run-skill csf-crosswalk --input <artifact.md>

Audit evidence for a control + period
  └─► spa run-skill evidence-pack --input <control+period.md> --output-dir .

Commercial product/tool risk assessment (findings + gaps)
  └─► spa run-skill risk-analyst --input <assessment.md>

Open-source / local repo security review (OWASP, ASVS, dependencies)
  └─► spa run-skill repo-security-review --input <repo-target.md>

Program status / morning triage
  └─► spa run-skill daily-brief --input <context.md>
```

### Ingest auto-detection (`spa ingest`)

Ingest always: redacts secrets/PII → writes episodic (SQLite) + semantic (Qdrant) memory.

If content looks like a **meeting** (≥2 signals among: `decisions`, `action items`, `risks`, `transcript`, `meeting`, `attendees`), ingest also:

1. Runs `meeting-synth` on redacted content
2. Creates **AI-Proposed** ticket JSON for each `proposed_tickets` entry (`assignee: unassigned`)
3. Runs `policy-redline` when action items or body mention policy/MFA/redline/update

If content does **not** match meeting signals, ingest only indexes memory — no downstream skills.

---

## Storage paths (how to build the right path)

Path resolution is centralized in `spa/paths.py`. Defaults below assume no env overrides.

### Environment overrides

| Variable | Default | Effect |
|----------|---------|--------|
| `SPA_DATA_DIR` | `workspace/.data` | Root for SQLite, drafts, and (if set) proposals |
| `SPA_AUDIT_DIR` | `governance/audit-logs` | Audit JSONL directory |
| `SPA_APPROVAL_QUEUE_DIR` | `governance/approval-queue` | CPO queue |

When `SPA_DATA_DIR` is set, proposals move to `{SPA_DATA_DIR}/proposals` instead of `workspace/proposals`.

### Path resolver cheat sheet

| Helper | Resolves to (default) |
|--------|------------------------|
| `get_data_dir()` | `workspace/.data/` |
| `get_drafts_dir()` | `workspace/.data/drafts/` |
| `get_proposals_dir()` | `workspace/proposals/` |
| `get_audit_logs_dir()` | `governance/audit-logs/` |
| `get_approval_queue_dir()` | `governance/approval-queue/` |

> **Hermes MCP note:** `./scripts/setup-hermes.sh` mounts `brain/`, `inbox/`, and `workspace/drafts/` for chat file access. The `spa` skill runner writes skill JSON artifacts to `workspace/.data/drafts/` by default. Check both locations when looking for recent skill output, or pass `--output-dir workspace/drafts/<skill>` to align with the MCP mount.

### Allowed write surfaces (draft-by-default)

| Surface | Risk | What goes here |
|---------|------|----------------|
| `inbox/` | A0 read / A1 if you create files | Raw inputs awaiting `spa ingest` |
| `workspace/.data/drafts/<skill>/` | A1 | Skill JSON artifacts from `spa run-skill` (default) |
| `workspace/drafts/` | A1 | Optional output root (`--output-dir`); Hermes MCP mount |
| `workspace/proposals/` | A1–A2 | Ticket proposals, policy redlines, draft PR bodies |
| `workspace/proposals/tickets/` | A2 | AI-Proposed ticket JSON (`ticket-proposal-<id>.json`) |
| `workspace/proposals/03-policies/proposals/` | A1 | Policy redline Markdown from `policy-redline` skill |
| `brain/03-policies/proposals/` | A1 | Git-backed policy proposals (promote from workspace after review) |
| `brain/evidence/<control-slug>/` | A1 | Evidence indexes (see naming below) |
| `brain/` (other) | A1 read-mostly | Frameworks, controls, authoritative policies |
| `governance/approval-queue/` | A1 create / A3+ execute | CPO JSON — create via ToolGuard, not by hand |
| `governance/audit-logs/` | append-only | Never write directly — emitted by `spa` only |

**Never write without approval:** authoritative policies (`brain/03-policies/*.md` publish), external ticket systems, GRC platforms, merge PRs, assign humans to tickets.

### Per-artifact path patterns

Build paths with these conventions:

#### Skill JSON artifact (all skills via runner)

```
workspace/.data/drafts/<skill-name>/<skill-name>-<UTC-timestamp>.json
# Example: workspace/.data/drafts/meeting-synth/meeting-synth-20260607T144158Z.json
# Timestamp format: YYYYMMDDTHHMMSSZ (UTC)
```

#### AI-Proposed tickets

```
workspace/proposals/tickets/ticket-proposal-<ticket-id>.json
# ticket-id: slashes replaced with hyphens (e.g. AI-PROPOSED-001)
# Required fields: status=ai_proposed, assignee=unassigned
```

#### Policy redline (via `policy-redline` skill)

```
workspace/proposals/03-policies/proposals/<policy-slug>-redline.md
workspace/proposals/draft-pr-body-<policy-slug>.md
# policy-slug: kebab-case (e.g. access-control-policy)
# Parse from input line "Policy: access-control-policy" when present
```

After human review, promote redlines to `brain/03-policies/proposals/<policy-slug>-redline.md`.

#### Evidence pack

```
brain/evidence/<control-slug>/index-<YYYYMMDD>.md
brain/evidence/<control-slug>/findings-<YYYYMMDD>.json   # when cloud checks return data
# control-slug: control ID with dots → hyphens (CC6.1 → CC6-1)
# Input must include: Control: CC6.1  and  Period: 2026-Q2 (or similar)
```

To write directly into git-backed `brain/evidence/`, run:

```bash
spa run-skill evidence-pack --input <file> --output-dir .
```

Default `--output-dir` nests under `workspace/.data/drafts/evidence-pack/brain/evidence/...` — fine for staging, not for committed evidence.

#### Risk assessment (via `risk-analyst` skill)

```
workspace/proposals/risks/risk-proposal-<id>.json
workspace/proposals/risks/risk-assessment-<product-slug>.md
workspace/proposals/risks/threat-model-<product-slug>.md
# Input: Product/Vendor + ## Findings and/or ## Gaps; optional ## Architecture, ## Integrations, ## Research notes
# Methodology: NIST SP 800-30 + FAIR-aligned semi-quantitative (1–5) + STRIDE threat model
```

Promote reviewed assessments to `brain/06-risks/<risk-slug>.md`.

#### Repo security review (via `repo-security-review` skill)

```
workspace/proposals/repo-security-review-<YYYYMMDD>.md
workspace/.data/drafts/repo-security-review/repo-security-review-<timestamp>.json
# Input: Repo: <path or https URL>, optional Branch:, Focus:
```

#### Daily brief

```
workspace/proposals/daily-brief-<YYYYMMDD>.md
# Or under custom --output-dir if passed
```

#### CPO (Change Proposal Object)

```
governance/approval-queue/cpo-<uuid>.json
# Created by spa ToolGuard for A3+ actions — do not fabricate or edit without CLI
```

#### Audit events

```
governance/audit-logs/<YYYY-MM-DD>.jsonl
# Append-only, hash-chained — spa emits these; agents must not truncate or delete (A5)
```

---

## Security Brain layout (`brain/`)

Git-backed knowledge base. Numbered dirs are canonical per `brain/00-meta/README.md`:

| Path | Contents |
|------|----------|
| `brain/00-meta/` | Brain conventions |
| `brain/01-frameworks/` | CSF 2.0, SOC 2, ISO 27001 overviews and crosswalks |
| `brain/02-controls/` | Control catalog (`cloud-checks.yaml` maps CC IDs → cloud checks) |
| `brain/03-policies/` | Authoritative policies; **`proposals/`** for draft redlines |
| `brain/04-standards/` | Standards baseline |
| `brain/05-procedures/` | Runbooks |
| `brain/06-risks/` | Risk register |
| `brain/07-evidence/` | Reserved in meta layout |
| `brain/evidence/<CC-slug>/` | Evidence indexes (active convention in MVP) |
| `brain/08-decisions/` | Decision log |

After adding or changing brain Markdown/YAML: `make seed` (re-index semantic memory).

---

## Skills reference

All skills: `spa run-skill <name> --input <path> [--output-dir <dir>]`

| Skill | Input | Primary outputs | Default output root |
|-------|-------|-----------------|---------------------|
| `meeting-synth` | Meeting notes / transcript | decisions, risks, action_items, proposed_tickets JSON | `workspace/.data/drafts/meeting-synth/` |
| `ticket-draft` | Issue description + control hints | `ticket-proposal-*.json` | `workspace/proposals/` (or `--output-dir`) |
| `policy-redline` | Change request (`Policy: <slug>` optional) | redline `.md`, draft PR body | `workspace/proposals/` |
| `csf-crosswalk` | Policy excerpt / vendor artifact | control_mappings, gaps | skill JSON artifact only |
| `daily-brief` | Optional context note | `daily-brief-*.md` | `workspace/proposals/` |
| `evidence-pack` | `Control: …` + `Period: …` (+ optional `Provider: aws`) | evidence index (+ findings JSON) | use `--output-dir .` for `brain/evidence/` |
| `risk-analyst` | Product/vendor + findings/gaps + optional architecture | risk proposal, assessment report, STRIDE threat model, implementation plan | `workspace/proposals/risks/` |
| `repo-security-review` | `Repo:` path or Git URL + optional `Focus:` | risk-scored findings JSON, brief report with ATT&CK mapping | `workspace/proposals/` |

Skill definitions (schemas, rubrics): `skills/<skill-name>/`. Python implementations: `spa/skills/`.

Verifiers run automatically; a second failure creates a CPO and **blocks** artifact write.

---

## Control tag format

Emit tags in outputs and tickets using this pattern:

```
CSF:<function>.<category>     e.g. CSF:PR.IP-12
SOC2:<CC-id>                  e.g. SOC2:CC6.1
800-53:<control>              e.g. 800-53:AC-2
```

Crosswalk references: `brain/01-frameworks/soc2-csf-crosswalk.md`, `brain/01-frameworks/csf-2.0-core.md`.

---

## Action-risk gates (A0–A5)

Classify every tool call per `agent/autonomy-policy.yaml`:

| Class | Label | Approval | Agent may |
|-------|-------|----------|-----------|
| **A0** | read | none | Read brain/inbox/workspace, search memory, ingest |
| **A1** | local_draft | none | Write drafts, create git branches, workspace/brain proposals |
| **A2** | external_draft | notify | AI-Proposed ticket files, draft PR bodies |
| **A3** | human_workflow | **CPO required** | Assign human, raise priority, terminal ticket state |
| **A4** | authoritative_record | **CPO required** | Merge PR, publish policy, GRC write, memory forget |
| **A5** | high_risk | **blocked** | Prod IAM, delete audit/evidence, risk acceptance, **unknown tools** |

A3+ actions create a CPO in `governance/approval-queue/` and block until approved:

```bash
spa proposals list
spa proposals show cpo-<uuid>
spa proposals approve cpo-<uuid>
spa proposals reject cpo-<uuid> --reason "..."
```

---

## Common workflows

### Drop-and-process (fastest path)

```bash
# 1. Write or receive raw notes
#    inbox/2026-06-07-steering-committee.md

source .venv/bin/activate
spa ingest inbox/2026-06-07-steering-committee.md
# → memory indexed
# → meeting-synth JSON in workspace/.data/drafts/meeting-synth/
# → tickets in workspace/proposals/tickets/
# → optional policy redline in workspace/proposals/03-policies/proposals/
```

### Run one skill explicitly

```bash
spa run-skill meeting-synth --input evals/fixtures/meeting_sample.md
spa run-skill ticket-draft --input evals/fixtures/ticket_input.md
spa run-skill policy-redline --input evals/fixtures/policy_change.md
spa run-skill csf-crosswalk --input evals/fixtures/crosswalk_input.md
spa run-skill evidence-pack --input evals/fixtures/evidence_pack_input.md --output-dir .
spa run-skill risk-analyst --input evals/fixtures/risk_analyst_input.md
spa run-skill repo-security-review --input evals/fixtures/repo_security_review_input.md
spa run-skill daily-brief --input evals/fixtures/daily_brief_context.md
```

### Review cycle

1. Inspect artifacts under `workspace/.data/drafts/`, `workspace/proposals/tickets/`, and proposal redlines.
2. For tickets: keep `assignee: unassigned` until human approves via CPO.
3. Promote reviewed policy redlines into `brain/03-policies/proposals/`.
4. Promote evidence indexes into `brain/evidence/<CC-slug>/`.
5. `make seed` after brain updates.

### Verify audit trail

```bash
spa audit verify
spa evidence export --output /tmp/pga-evidence.tar.gz
```

---

## Memory

| Layer | Location | Populate |
|-------|----------|----------|
| Episodic | `workspace/.data/` (SQLite) | `spa ingest`, guarded writes |
| Semantic | Qdrant `:6333` | `make seed`, ingest upserts |
| Procedural | `skills/` | versioned in git |
| Audit | `governance/audit-logs/` | every spa action |

Bootstrap: `./bootstrap.sh` then `make seed`. Re-seed after brain changes.

Redaction runs at write time per `governance/redaction-rules.yaml` — never persist secrets or PII.

---

## Do / don't

**Do**

- Prefer `spa ingest` and `spa run-skill` for governed artifacts.
- Keep tickets `status: ai_proposed`, `assignee: unassigned` in MVP.
- Tag outputs with CSF / SOC2 / 800-53 control references.
- Suggest owners; never auto-assign without approved CPO.
- Use `evals/fixtures/` as input examples when unsure of format.

**Don't**

- Assign tickets to humans, publish policies, or merge PRs without approved CPO (A3/A4).
- Write directly to `governance/audit-logs/` or delete evidence (A5).
- Bypass ToolGuard by mimicking skill output files when verifiers matter.
- Commit `.env`, credentials, or unredacted secrets.
- Treat `workspace/proposals/` or `brain/03-policies/proposals/` as authoritative — they are drafts until a human publishes.

---

## CLI quick reference

```bash
source .venv/bin/activate

spa ingest <path>                          # ingest + auto-pipeline
spa run-skill <skill> --input <path>       # run one skill
spa run-skill <skill> --input <path> --output-dir <dir>

spa proposals list|show|approve|reject     # CPO workflow
spa audit verify [--from DATE] [--to DATE] # hash chain check
spa mcp serve                              # governed MCP server (stdio)
spa evidence export --output <file.tar.gz> # auditor bundle

make seed      # re-index brain → Qdrant
make selftest  # health checks
make eval      # golden skill evals
```

---

## Key files for agents

| File | Purpose |
|------|---------|
| `agent/charter.md` | Persona and principles |
| `agent/autonomy-policy.yaml` | Risk gates and tool → class mappings |
| `agent/runtime.config.yaml` | Runtime swap (Hermes default) |
| `spa/paths.py` | **Canonical path resolution** |
| `governance/redaction-rules.yaml` | Secret/PII patterns |
| `memory/schemas/*.schema.json` | CPO, audit event, memory object shapes |
| `skills/*/skill.md` | Per-skill contract |
| `evals/fixtures/` | Sample inputs for every skill |

---

## Hermes / Cursor / Claude Code

### Connect any MCP client (governed)

`spa mcp serve` exposes ToolGuard-wrapped tools over stdio (FastMCP). Config: `mcp/pga-governed.json`.

| Tool | Delegates to |
|------|----------------|
| `pga_ingest` | `spa ingest` |
| `pga_run_skill` | `spa run-skill` |
| `pga_proposals_list` / `pga_proposals_show` | approval queue reads |
| `pga_proposals_approve` / `pga_proposals_reject` | CPO workflow (**A3** — requires `confirm: true`; clients must surface to human) |
| `pga_audit_verify` | hash chain verify |
| `pga_memory_search` | episodic FTS + semantic search |

Wire Hermes: `./scripts/setup-hermes.sh` registers **`pga-governed`** only (removes any legacy `pga-filesystem` mount).

- **Hermes:** Launch from repo root (`hermes chat`) so this file loads. Use **`pga-governed`** MCP for ingest/skills; browse `brain/` in your editor or via `pga_memory_search`.
- **Cursor / Claude Code:** This `AGENTS.md` is the workspace rule source. Follow draft-by-default; use terminal `spa` commands for verifiable skill runs.
- **Cursor rules:** File-scoped path guidance in `.cursor/rules/` — `pga-core.mdc` (always on), `pga-brain-paths.mdc`, `pga-workspace-paths.mdc`, `pga-inbox-paths.mdc`.
- **Both:** Explore in chat → execute with `spa` → review artifacts → human approves CPOs for anything A3+.
